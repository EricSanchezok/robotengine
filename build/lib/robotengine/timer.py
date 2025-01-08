from .node import Node
import threading
import time
from .signal import Signal

class Timer(Node):
    def __init__(self, name="Timer", autostart=False, one_shot=False, paused=False, wait_time=1.0):
        super().__init__(name)
        self.time_left = 0.0
        self.wait_time = wait_time
        self.autostart = autostart
        self.one_shot = one_shot
        self.paused = paused

        self._running = False
        
        self.timeout = Signal()  # 超时信号

        if autostart:
            self.start()

    def _timer(self, delta):
        if self.paused or not self._running:
            return
        
        if self.time_left > 0:
            self.time_left = max(0, self.time_left - delta)
            if self.time_left <= 0:
                self.timeout.emit()
                if self.one_shot:
                    self.stop()
                else:
                    self.time_left = self.wait_time

    def is_stopped(self) -> bool:
        return not self._running

    def start(self) -> None:
        self._running = True
        self.time_left = self.wait_time

    def stop(self) -> None:
        self._running = False
