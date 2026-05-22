import threading
import time
import os
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
import cv2  # used for JPEG encoding in get_jpeg()

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
        self.record_filename   = None   # base path (no extension)
        self.recording_encoder = None
        self._segment_index    = 0
        self._segment_paths    = []     # ordered list of raw .h264 paths
        self._segment_timer    = None
        self._segment_lock     = threading.Lock()

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

            self._segment_index += 1
            self._start_segment()

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
            print(f"[INFO] Recording stopped — {len(self._segment_paths)} segment(s) saved.")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

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