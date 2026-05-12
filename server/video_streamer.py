import threading
import time
import subprocess
import numpy as np
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
import cv2
import os

class CameraBusyException(Exception):
    pass

class VideoStreamer:
    def __init__(self):
        self.picam2 = Picamera2()
        # Configure for preview/livestream
        preview_config = self.picam2.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        self.picam2.configure(preview_config)
        self.picam2.start()
        self.recording = False
        self.compressing = False   # True while background H.265 encode is running
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.record_filename = None
        self.recording_encoder = None
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()

    def _update_frame(self):
        while self.running:
            if not self.recording:  # Only capture frames when not recording
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

    def start_recording(self, filename="output.mp4"):
        print(f"[DEBUG] start_recording called. self.recording={self.recording} | thread alive: {self.thread.is_alive()}")
        if not self.recording:
            try:
                video_dir = os.path.join(os.path.dirname(__file__), "data", "videos")
                os.makedirs(video_dir, exist_ok=True)
                full_path = os.path.join(video_dir, filename)
                self.record_filename = full_path
                
                # Use H264Encoder for web compatibility
                encoder = H264Encoder()
                self.recording_encoder = self.picam2.start_encoder(
                    encoder=encoder,
                    output=full_path,
                    quality=Quality.HIGH
                )
                self.recording = True
                print(f"[DEBUG] Recording started to: {full_path}")
                
            except Exception as e:
                print(f"[ERROR] Failed to start recording: {e}")
                self.recording = False
                self.record_filename = None
                raise
        print(f"[DEBUG] start_recording finished. self.recording={self.recording} | thread alive: {self.thread.is_alive()}")

    def stop_recording(self):
        if self.recording:
            try:
                if self.recording_encoder:
                    self.picam2.stop_encoder(self.recording_encoder)
                    self.recording_encoder = None
                self.recording = False

                # Kick off H.265 compression in background so the API responds immediately
                if self.record_filename and os.path.exists(self.record_filename):
                    t = threading.Thread(
                        target=self._compress_to_h265,
                        args=(self.record_filename,),
                        daemon=True
                    )
                    t.start()

            except Exception as e:
                print(f"[ERROR] Error stopping recording: {e}")
                self.recording = False

    def _compress_to_h265(self, source_path):
        """Re-encode source file to H.265/HEVC in a background thread.

        Uses CRF 28 with the fast preset — roughly half the file size of
        H.264 Quality.HIGH at 640x480 with no perceptible quality loss.
        The original file is replaced atomically on success.
        """
        self.compressing = True
        temp_path = source_path + ".h265.tmp"
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", source_path,
                "-c:v", "libx265",
                "-crf", "28",
                "-preset", "fast",
                "-tag:v", "hvc1",          # broad browser/player compatibility
                "-movflags", "+faststart",  # move metadata to front for streaming
                temp_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                os.replace(temp_path, source_path)  # atomic swap
                print(f"[INFO] H.265 compression complete: {source_path}")
            else:
                print(f"[ERROR] ffmpeg H.265 encode failed:\n{result.stderr}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        except Exception as e:
            print(f"[ERROR] H.265 compression error: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
        finally:
            self.compressing = False
    
    def recording_completed_successfully(self):
        """Check if the last recording completed successfully and file is valid"""
        if not self.record_filename or not os.path.exists(self.record_filename):
            return False
        
        # Check file size (should be > 1KB for valid video)
        file_size = os.path.getsize(self.record_filename)
        return file_size > 1024

    def release(self):
        print(f"[DEBUG] release called. Thread alive before: {self.thread.is_alive()}")
        self.running = False
        
        # Stop recording if active
        if self.recording:
            self.stop_recording()
        
        # Wait for thread to finish
        if self.thread.is_alive():
            self.thread.join(timeout=3)
            
        # Clean up camera
        try:
            if self.recording_encoder:
                self.picam2.stop_encoder(self.recording_encoder)
            self.picam2.stop()
            self.picam2.close()
        except Exception as e:
            print(f"[DEBUG] Error releasing camera: {e}")
            
        print(f"[DEBUG] release finished. Thread alive after: {self.thread.is_alive()}")