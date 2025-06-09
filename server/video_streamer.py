import cv2
import threading
import time

class VideoStreamer:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.recording = False
        self.writer = None
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        threading.Thread(target=self._update_frame, daemon=True).start()

    def _update_frame(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
                if self.recording and self.writer:
                    self.writer.write(frame)
            else:
                time.sleep(0.1)  # Avoid busy loop if no frame

    def get_jpeg(self):
        with self.lock:
            if self.frame is None:
                return None
            ret, jpeg = cv2.imencode('.jpg', self.frame)
            return jpeg.tobytes() if ret else None

    def start_recording(self, filename="output.avi"):
        if not self.recording:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            with self.lock:
                if self.frame is not None:
                    h, w = self.frame.shape[:2]
                else:
                    h, w = 480, 640  # default
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
        self.cap.release()