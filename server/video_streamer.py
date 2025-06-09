import threading
import time
import numpy as np
from picamera2 import Picamera2, Preview
import cv2

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
            threading.Thread(target=self._update_frame, daemon=True).start()
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
            bgr_frame = cv2.cvtColor(self.frame, cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.jpg', bgr_frame)
            return jpeg.tobytes() if ret else None

    def start_recording(self, filename="output.avi"):
        if not self.recording:
            with self.lock:
                if self.frame is not None:
                    h, w = self.frame.shape[:2]
                else:
                    h, w = 480, 640  # default
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                self.writer = cv2.VideoWriter(filename, fourcc, 20.0, (w, h))
            self.recording = True

    def stop_recording(self):
        if self.recording:
            self.recording = False
            if self.writer:
                self.writer.release()
                self.writer = None

    def release(self):
        self.running = False
        self.stop_recording()
        self.picam2.stop()