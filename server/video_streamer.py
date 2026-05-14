import threading
import time
import subprocess
import queue
import os
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
import cv2

class CameraBusyException(Exception):
    pass

# Rotate to a new segment every 30 minutes so no single raw file exceeds ~325 MB.
SEGMENT_DURATION_SECS = 1800

class VideoStreamer:
    def __init__(self):
        self.picam2 = Picamera2()
        preview_config = self.picam2.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        self.picam2.configure(preview_config)
        self.picam2.start()

        self.recording  = False
        self.frame      = None
        self.lock       = threading.Lock()
        self.running    = True

        # Per-recording state (reset in start_recording)
        self.record_filename         = None   # base path (no extension)
        self.recording_encoder       = None
        self._segment_index          = 0
        self._segment_paths          = []     # ordered list of raw .h264 paths
        self._queued_for_compression = set()
        self._segment_timer          = None
        self._segment_lock           = threading.Lock()

        # Compression state — exposed to main.py for the progress endpoint
        self.compressing = False
        self.compression_progress = {
            "active":         False,
            "current_file":   None,
            "percent":        0,
            "segments_done":  0,
            "segments_total": 0,
        }

        self._compression_queue = queue.Queue()
        # Non-daemon: an in-flight compress finishes even if the Flask process exits.
        self._compression_thread = threading.Thread(
            target=self._compression_worker, daemon=False
        )
        self._compression_thread.start()

        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()

    # ── Frame capture (preview / livestream only) ──────────────────────────────

    def _update_frame(self):
        while self.running:
            if not self.recording:
                try:
                    with self.lock:
                        self.frame = self.picam2.capture_array()
                except Exception as e:
                    print(f"[DEBUG] Error capturing frame: {e}")
                    with self.lock:
                        self.frame = None
            time.sleep(0.03)  # ~30 FPS

    def get_jpeg(self):
        with self.lock:
            if self.frame is None:
                return None
            ret, jpeg = cv2.imencode('.jpg', self.frame)
            return jpeg.tobytes() if ret else None

    # ── Recording ─────────────────────────────────────────────────────────────

    def start_recording(self, filename="output.mp4"):
        if self.recording:
            return

        video_dir = os.path.join(os.path.dirname(__file__), "data", "videos")
        os.makedirs(video_dir, exist_ok=True)

        # Remove stale temp files left over from a previous crash.
        for f in os.listdir(video_dir):
            if f.endswith(".tmp.mp4"):
                try:
                    os.remove(os.path.join(video_dir, f))
                    print(f"[INFO] Removed stale temp file: {f}")
                except OSError:
                    pass

        base = os.path.splitext(filename)[0]
        self.record_filename = os.path.join(video_dir, base)
        self._segment_index = 0
        self._segment_paths = []
        self._queued_for_compression = set()
        self.compression_progress = {
            "active": False, "current_file": None,
            "percent": 0, "segments_done": 0, "segments_total": 0,
        }

        self._start_segment()
        self.recording = True
        print(f"[INFO] Recording started (segments ≤{SEGMENT_DURATION_SECS}s): {self.record_filename}")

    def _start_segment(self):
        """Open a new .h264 segment and schedule its rotation."""
        seg_path = f"{self.record_filename}_seg{self._segment_index:03d}.h264"
        self._segment_paths.append(seg_path)

        encoder = H264Encoder()
        # Quality.MEDIUM keeps raw segment size under ~325 MB at 640×480 / 30 min.
        self.recording_encoder = self.picam2.start_encoder(
            encoder=encoder, output=seg_path, quality=Quality.MEDIUM
        )

        self._segment_timer = threading.Timer(SEGMENT_DURATION_SECS, self._rotate_segment)
        self._segment_timer.daemon = True
        self._segment_timer.start()
        print(f"[INFO] Segment {self._segment_index} started: {os.path.basename(seg_path)}")

    def _rotate_segment(self):
        """Close the current segment, open the next, and queue the closed one for compression."""
        with self._segment_lock:
            if not self.recording:
                return
            if self.recording_encoder:
                try:
                    self.picam2.stop_encoder(self.recording_encoder)
                except Exception as e:
                    print(f"[WARN] Rotation encoder stop error: {e}")
                self.recording_encoder = None

            completed = self._segment_paths[-1]
            self._segment_index += 1
            self._start_segment()
            self._enqueue_segment(completed)

    def stop_recording(self):
        with self._segment_lock:
            if not self.recording:
                return
            if self._segment_timer:
                self._segment_timer.cancel()
                self._segment_timer = None
            if self.recording_encoder:
                try:
                    self.picam2.stop_encoder(self.recording_encoder)
                except Exception as e:
                    print(f"[WARN] Stop encoder error: {e}")
                self.recording_encoder = None

            self.recording = False
            total = len(self._segment_paths)
            self.compression_progress["segments_total"] = total

            if self._segment_paths:
                self._enqueue_segment(self._segment_paths[-1])

            print(f"[INFO] Recording stopped — {total} segment(s) queued for compression.")

    def _enqueue_segment(self, path):
        if path in self._queued_for_compression:
            return
        if not os.path.exists(path):
            print(f"[WARN] Segment file not found, skipping: {path}")
            return
        self._queued_for_compression.add(path)
        self._compression_queue.put(path)
        self.compressing = True
        self.compression_progress["active"] = True
        print(f"[INFO] Queued for compression: {os.path.basename(path)}")

    # ── Compression worker ────────────────────────────────────────────────────

    def _compression_worker(self):
        """Sequentially compress queued .h264 segments to H.265 .mp4."""
        while True:
            try:
                path = self._compression_queue.get(timeout=2)
            except queue.Empty:
                continue
            if path is None:
                break
            self._compress_segment(path)
            self._compression_queue.task_done()
            if self._compression_queue.empty():
                self.compressing = False
                self.compression_progress["active"] = False

    def _get_video_duration(self, path):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                capture_output=True, text=True, timeout=30,
            )
            return float(result.stdout.strip())
        except Exception:
            return None

    def _compress_segment(self, source_path):
        """Re-encode one H.264 segment to H.265/HEVC with live progress tracking.

        Uses CRF 28 / fast preset — roughly half the file size of H.264 Quality.HIGH
        with no perceptible quality loss at 640×480.  The raw .h264 is removed
        atomically on success so storage is reclaimed as encoding proceeds.
        """
        seg_name    = os.path.basename(source_path)
        output_path = os.path.splitext(source_path)[0] + ".mp4"
        temp_path   = source_path + ".tmp.mp4"

        self.compression_progress.update({
            "active":       True,
            "current_file": seg_name,
            "percent":      0,
        })

        duration_s = self._get_video_duration(source_path)
        print(f"[INFO] Compressing {seg_name}"
              + (f" ({duration_s:.0f}s)" if duration_s else ""))

        cmd = [
            "ffmpeg", "-y",
            "-i", source_path,
            "-c:v", "libx265",
            "-crf", "28",
            "-preset", "fast",
            "-tag:v", "hvc1",           # broad player/browser compatibility
            "-movflags", "+faststart",  # move metadata to front for streaming
            "-progress", "pipe:1",      # machine-readable progress → stdout
            "-nostats",
            temp_path,
        ]

        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("out_time_ms=") and duration_s:
                    try:
                        ms = int(line.split("=")[1])
                        pct = min(99, int(ms / 1000 / duration_s * 100))
                        self.compression_progress["percent"] = pct
                    except (ValueError, ZeroDivisionError):
                        pass
            proc.wait()

            if proc.returncode == 0:
                os.replace(temp_path, output_path)   # atomic swap
                os.remove(source_path)               # reclaim raw H.264 storage
                self.compression_progress["segments_done"] = (
                    self.compression_progress.get("segments_done", 0) + 1
                )
                self.compression_progress["percent"] = 100
                print(f"[INFO] Compressed → {os.path.basename(output_path)}")
            else:
                print(f"[ERROR] ffmpeg failed for {seg_name}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            print(f"[ERROR] Compression error for {seg_name}: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def recording_completed_successfully(self):
        return bool(self._segment_paths) and any(
            os.path.exists(os.path.splitext(p)[0] + ".mp4")
            for p in self._segment_paths
        )

    def release(self):
        self.running = False
        if self.recording:
            self.stop_recording()
        if self.thread.is_alive():
            self.thread.join(timeout=3)
        try:
            if self.recording_encoder:
                self.picam2.stop_encoder(self.recording_encoder)
            self.picam2.stop()
            self.picam2.close()
        except Exception as e:
            print(f"[DEBUG] Error releasing camera: {e}")