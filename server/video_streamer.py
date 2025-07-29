import threading
import time
import subprocess
import numpy as np
from picamera2 import Picamera2
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
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.record_filename = None
        self.recording_encoder = None
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()
        print(f"[DEBUG] VideoStreamer thread started: {self.thread.is_alive()}")

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
                
                # Use H.264 encoder for web compatibility
                self.recording_encoder = self.picam2.start_encoder(
                    encoder='h264',
                    output=full_path,
                    quality='high'
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
        print(f"[DEBUG] stop_recording called. self.recording={self.recording} | thread alive: {self.thread.is_alive()}")
        if self.recording:
            try:
                if self.recording_encoder:
                    self.picam2.stop_encoder(self.recording_encoder)
                    self.recording_encoder = None
                
                self.recording = False
                
                # Convert H.264 to web-compatible MP4 using ffmpeg
                if self.record_filename and os.path.exists(self.record_filename):
                    self._convert_to_web_mp4(self.record_filename)
                    
                print(f"[DEBUG] Recording stopped and converted: {self.record_filename}")
                
            except Exception as e:
                print(f"[ERROR] Error stopping recording: {e}")
                self.recording = False
                
        print(f"[DEBUG] After stop_recording: self.recording={self.recording} | thread alive: {self.thread.is_alive()}")
    
    def _convert_to_web_mp4(self, h264_file):
        """Convert H.264 file to web-compatible MP4"""
        try:
            mp4_file = h264_file.replace('.h264', '.mp4') if h264_file.endswith('.h264') else h264_file
            temp_mp4 = mp4_file + '.tmp'
            
            # Use ffmpeg to create web-compatible MP4
            cmd = [
                'ffmpeg', '-y',
                '-i', h264_file,
                '-c:v', 'copy',  # Copy video stream (already H.264)
                '-movflags', 'faststart',  # Move metadata to beginning for web streaming
                '-f', 'mp4',
                temp_mp4
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Replace original with converted file
                os.replace(temp_mp4, mp4_file)
                if h264_file != mp4_file and os.path.exists(h264_file):
                    os.remove(h264_file)  # Clean up H.264 file
                print(f"[DEBUG] Successfully converted to web-compatible MP4: {mp4_file}")
            else:
                print(f"[ERROR] ffmpeg conversion failed: {result.stderr}")
                if os.path.exists(temp_mp4):
                    os.remove(temp_mp4)
                    
        except Exception as e:
            print(f"[ERROR] Conversion error: {e}")
    
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