"""
Timer 是 robotengine 中异步操作的基础。

Timer 继承自 Node 节点，可以在节点树中进行管理。

"""
from robotengine.node import Node
import threading
import time
from robotengine.signal import Signal

class Timer(Node):
    """ 计时器类 """
    def __init__(self, name="Timer", autostart: bool=False, one_shot: bool=False, paused: bool=False, wait_time: float=1.0):
        """ 初始化计时器 """
        super().__init__(name)
        self.time_left: float = 0.0
        """ 剩余时间 """
        self.wait_time: float = wait_time
        """ 等待时间 """
        self.autostart: float = autostart
        """ 是否自动启动， 如果为 True 则会在当前节点 _ready() 时自动启动 """
        self.one_shot = one_shot
        """ 是否为一次性计时器， 如果为 True 则会在触发一次后停止  """
        self.paused = paused
        """ 是否暂停， 如果为 True 则停止计时 """

        self._running = False
        
        self.timeout = Signal()
        """ 信号，当计时器计时结束时触发 """

    def _ready(self):
        if self.autostart:
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
        """ 判断计时器是否停止 """
        return not self._running

    def start(self) -> None:
        """ 启动计时器 """
        self._running = True
        self.time_left = self.wait_time

    def stop(self) -> None:
        """ 停止计时器 """
        self._running = False
        self.time_left = 0.0
