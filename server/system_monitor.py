import threading
import time
import psutil

class SystemMonitor:
    def __init__(self, interval=1):
        self.interval = interval
        self.data = {
            'cpu_percent': 0.0,
            'ram_percent': 0.0,
            'ram_used': 0,
            'ram_total': 0,
            'timestamp': time.time(),
        }
        self.running = False
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._monitor, daemon=True)

    def start(self):
        self.running = True
        if not self.thread.is_alive():
            self.thread = threading.Thread(target=self._monitor, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join(timeout=2)

    def _monitor(self):
        while self.running:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            with self.lock:
                self.data = {
                    'cpu_percent': cpu,
                    'ram_percent': mem.percent,
                    'ram_used': mem.used,
                    'ram_total': mem.total,
                    'timestamp': time.time(),
                }
            time.sleep(self.interval)

    def get_data(self):
        with self.lock:
            return dict(self.data)

# Singleton instance
system_monitor = SystemMonitor()
system_monitor.start()
