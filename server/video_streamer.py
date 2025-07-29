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
        self.picam2 = None
        self.recording = False
        self.writer = None
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        print(f"[DEBUG] VideoStreamer thread started: {self.thread.is_alive()}")

    def _update_frame(self):
        while self.running:
            if self.picam2 is None:
                # Camera not acquired (e.g., during recording)
                time.sleep(0.1)
                continue
            try:
                frame = self.picam2.capture_array()  # Returns a numpy array (RGB)
            except Exception as e:
                print(f"[DEBUG] Error capturing frame: {e}")
                frame = None
            with self.lock:
                self.frame = frame
            time.sleep(0.03)  # ~30 FPS

    def start_recording(self, filename="output.mp4"):
        print(f"[DEBUG] start_recording called. self.recording={getattr(self, 'recording', None)} | thread alive: {self.thread.is_alive()}")
        if not self.recording:
            with self.lock:
                # Release Picamera2 if acquired
                if self.picam2:
                    try:
                        self.picam2.stop()
                        self.picam2.close()
                    except Exception as e:
                        print(f"[DEBUG] Error releasing Picamera2 before recording: {e}")
                    self.picam2 = None
                video_dir = os.path.join(os.path.dirname(__file__), "data", "videos")
                os.makedirs(video_dir, exist_ok=True)
                filename = os.path.join(video_dir, filename)
                self._recording_proc = None
                h, w = (480, 640)
                if self.frame is not None:
                    h, w = self.frame.shape[:2]
                cmd = [
                    "rpicam-vid",
                    "-o", filename,
                    "-t", "0",
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
            # Reacquire Picamera2 for preview/live streaming
            with self.lock:
                if self.picam2 is None:
                    try:
                        self.picam2 = Picamera2()
                        video_config = self.picam2.create_video_configuration(
                            main={"size": (640, 480), "format": "RGB888"}
                        )
                        self.picam2.configure(video_config)
                        self.picam2.start()
                        print("[DEBUG] Picamera2 reacquired after recording.")
                    except RuntimeError as e:
                        print(f"[DEBUG] Error reacquiring Picamera2: {e}")
        print(f"[DEBUG] After stop_recording: self.recording={self.recording} | thread alive: {self.thread.is_alive()}")

    def release(self):
        print(f"[DEBUG] release called. Thread alive before: {self.thread.is_alive()}")
        self.running = False
        self.stop_recording()
        self.thread.join(timeout=3)
        print(f"[DEBUG] release finished. Thread alive after: {self.thread.is_alive()}")
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except Exception as e:
                print(f"[DEBUG] Error releasing Picamera2: {e}")
            self.picam2 = None