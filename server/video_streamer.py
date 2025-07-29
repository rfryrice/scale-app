import threading
import time
import numpy as np
from picamera2 import Picamera2
import cv2
import os

class CameraBusyException(Exception):
    pass

class VideoStreamer:
    def __init__(self):
        self.picam2 = Picamera2()
        video_config = self.picam2.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        self.picam2.configure(video_config)
        self.picam2.start()
        self.recording = False
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.record_filename = None
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        print(f"[DEBUG] VideoStreamer thread started: {self.thread.is_alive()}")

    def _update_frame(self):
        while self.running:
            with self.lock:
                if not self.recording:
                    try:
                        self.frame = self.picam2.capture_array()
                    except Exception as e:
                        print(f"[DEBUG] Error capturing frame: {e}")
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
            with self.lock:
                video_dir = os.path.join(os.path.dirname(__file__), "data", "videos")
                os.makedirs(video_dir, exist_ok=True)
                filename = os.path.join(video_dir, filename)
                self.record_filename = filename
                self.picam2.stop()
                video_config = self.picam2.create_video_configuration(
                    main={"size": (640, 480), "format": "RGB888"}
                )
                self.picam2.configure(video_config)
                self.picam2.start()
                self.picam2.start_recording(filename)
                self.recording = True
        print(f"[DEBUG] start_recording finished. self.recording={self.recording} | thread alive: {self.thread.is_alive()}")

    def stop_recording(self):
        print(f"[DEBUG] stop_recording called. self.recording={self.recording} | thread alive: {self.thread.is_alive()}")
        if self.recording:
            with self.lock:
                self.picam2.stop_recording()
                self.recording = False
        print(f"[DEBUG] After stop_recording: self.recording={self.recording} | thread alive: {self.thread.is_alive()}")

    def release(self):
        print(f"[DEBUG] release called. Thread alive before: {self.thread.is_alive()}")
        self.running = False
        if self.recording:
            self.stop_recording()
        self.thread.join(timeout=3)
        print(f"[DEBUG] release finished. Thread alive after: {self.thread.is_alive()}")
        self.picam2.stop()
        self.picam2.close()