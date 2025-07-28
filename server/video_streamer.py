import threading
import subprocess
import time
import numpy as np
from picamera2 import Picamera2, Preview
import cv2
import os

class CameraBusyException(Exception):
    pass

class VideoStreamer:
    def __init__(self):

        try:
            self.picam2 = Picamera2()
            # Configure camera
            video_config = self.picam2.create_video_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            )
            self.picam2.configure(video_config)
            self.picam2.start()
            self.recording = False
            self.writer = None
            self.frame = None
            self.lock = threading.Lock()
            self.running = True
            self.thread = threading.Thread(target=self._update_frame, daemon=True)
            self.thread.start()
            print(f"[DEBUG] VideoStreamer thread started: {self.thread.is_alive()}")
        except RuntimeError as e:
            if "Device or resource busy" in str(e) or "Pipeline handler in use by another process" in str(e):
                raise CameraBusyException("Camera is currently in use.")
            else:
                raise

    def _update_frame(self):
        while self.running:
            frame = self.picam2.capture_array()  # Returns a numpy array (RGB)
            with self.lock:
                self.frame = frame
            if self.recording and self.writer and self.frame is not None:
                # OpenCV expects BGR format
                bgr_frame = cv2.cvtColor(self.frame, cv2.COLOR_RGB2BGR)
                self.writer.write(bgr_frame)
            time.sleep(0.03)  # ~30 FPS

    def get_jpeg(self):
        with self.lock:
            if self.frame is None:
                return None
            # Convert RGB to BGR for OpenCV
            # bgr_frame = cv2.cvtColor(self.frame, cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.jpg', self.frame)
            return jpeg.tobytes() if ret else None

    def start_recording(self, filename="output.mp4"):
        print(f"[DEBUG] start_recording called. self.recording={getattr(self, 'recording', None)} | thread alive: {self.thread.is_alive()}")
        if not self.recording:
            with self.lock:
                video_dir = os.path.join(os.path.dirname(__file__), "data", "videos")
                os.makedirs(video_dir, exist_ok=True)
                filename = os.path.join(video_dir, filename)
                # Use rpicam-vid for H.264 hardware encoding
                self._recording_proc = None
                h, w = (480, 640)
                if self.frame is not None:
                    h, w = self.frame.shape[:2]
                # rpicam-vid expects width x height
                cmd = [
                    "rpicam-vid",
                    "-o", filename,
                    "-t", "0",  # unlimited duration, will be killed on stop
                    "--width", str(w),
                    "--height", str(h),
                    "--codec", "h264",
                    "--framerate", "20"
                ]
                print(f"[DEBUG] Starting rpicam-vid: {' '.join(cmd)}")
                
                self._recording_proc = subprocess.Popen(cmd)
            self.recording = True
        print(f"[DEBUG] start_recording finished. self.recording={getattr(self, 'recording', None)} | thread alive: {self.thread.is_alive()}")

    def stop_recording(self):
        print(f"[DEBUG] stop_recording called. self.recording={self.recording} | thread alive: {self.thread.is_alive()}")
        if self.recording:
            self.recording = False
            # Stop rpicam-vid process if running
            if hasattr(self, '_recording_proc') and self._recording_proc:
                print("[DEBUG] Terminating rpicam-vid process...")
                self._recording_proc.terminate()
                try:
                    self._recording_proc.wait(timeout=5)
                except Exception:
                    self._recording_proc.kill()
                self._recording_proc = None
        print(f"[DEBUG] After stop_recording: self.recording={self.recording} | thread alive: {self.thread.is_alive()}")

    def release(self):
        print(f"[DEBUG] release called. Thread alive before: {self.thread.is_alive()}")
        self.running = False
        self.stop_recording()
        self.thread.join(timeout=3)
        print(f"[DEBUG] release finished. Thread alive after: {self.thread.is_alive()}")
        self.picam2.stop()
        self.picam2.close()