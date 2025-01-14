""" 

引擎是 robotengine 的核心部分，负责管理节点的初始化、运行和更新。

Engine 同时还存储了一些全局变量，如帧数 frame 和时间戳 timestamp等。

在 Node 类中可以通过使用 self.engine 来访问引擎。

"""
import threading
import time
from enum import Enum
from robotengine.input import Input, GamepadListener
from robotengine.node import ProcessMode
from robotengine.tools import warning, error, info
from robotengine.signal import Signal
import multiprocessing
from typing import List, Tuple

class InputDevice(Enum):
    """ 输入设备枚举 """
    KEYBOARD = 0
    """ 键盘输入 """
    MOUSE = 1
    """ 鼠标输入 """
    GAMEPAD = 2
    """ 手柄输入 """


class Engine:
    """ 引擎类 """
    from robotengine.node import Node
    def __init__(self, root: Node, frequency: float=180, input_devices: List[InputDevice]=[]):
        """
        初始化引擎

            :param root (Node): 根节点
            :param frequency (int, optional): 影响所有节点的 _process 函数的调用频率。
            :param input_devices (list, optional): 输入设备列表，当为空时，节点的 _input() 函数将不会被调用。
        """
        self.root = root
        """ 根节点 """
        self.paused = False
        """ 是否暂停 """

        self._frequency = frequency
        self._frame = 0
        self._start_timestamp = 0
        self._timestamp = 0
        self._time_frequency = 30

        self.input = Input()
        """ 输入类， 在 Engine 初始化完成后，每个 Node 都可以通过 self.input 来访问输入类 """

        self.engine_exit = Signal()
        """ 退出信号，当引擎退出时触发 """

        self._initialize()

        self._threads = []
        self._shutdown = threading.Event()
        if input_devices:
            if InputDevice.GAMEPAD in input_devices:
                self._gamepad_listener = GamepadListener()

            self._input_thread = threading.Thread(target=self._do_input, daemon=True, name="EngineInputThread")
            self._threads.append(self._input_thread)

        self._update_thread = threading.Thread(target=self._do_update, daemon=True, name="EngineUpdateThread")
        self._threads.append(self._update_thread)

        self._timer_thread = threading.Thread(target=self._do_timer, daemon=True, name="EngineTimerThread")
        self._threads.append(self._timer_thread)


    def _initialize(self):
        from robotengine.node import Node
        def init_recursive(node: Node):
            for child in node.get_children():
                init_recursive(child)
            
            node.engine = self
            node.input = self.input
            
            node._init()
            self.engine_exit.connect(node._on_engine_exit)

        def ready_recursive(node: Node):
            for child in node.get_children():
                ready_recursive(child)
            node._do_ready()

        init_recursive(self.root)
        ready_recursive(self.root)

    def _do_update(self):
        from robotengine.node import Node
        def process_update(delta):
            def update_recursive(node: Node, delta):
                for child in node.get_children():
                    update_recursive(child, delta)
                node._update(delta)
            update_recursive(self.root, delta)

        self._run_loop(1, precise_control=False, process_func=process_update)

    def _do_timer(self):
        from robotengine.node import Node
        def process_timer(delta):
            def timer_recursive(node: Node, delta):
                for child in node.get_children():
                    timer_recursive(child, delta)
                node._timer(delta)
            timer_recursive(self.root, delta)

        self._run_loop(self._time_frequency, precise_control=False, process_func=process_timer)
            
    def _do_input(self):
        from robotengine.node import Node
        from robotengine.input import InputEvent
        def input_recursive(node: Node, event: InputEvent):
            for child in node.get_children():
                input_recursive(child, event)
            node._input(event)

        while not self._shutdown.is_set():
            if self._gamepad_listener:
                for _gamepad_event in self._gamepad_listener.listen():
                    self.input._update(_gamepad_event)
                    input_recursive(self.root, _gamepad_event)

    def run(self):
        """ 
        开始运行引擎 
        """
        from robotengine.node import Node
        def do_process(delta):
            def process_recursive(node: Node):
                if self.paused:
                    if node.process_mode == ProcessMode.WHEN_PAUSED or node.process_mode == ProcessMode.ALWAYS:
                        node._process(delta)
                else:
                    if node.process_mode == ProcessMode.PAUSABLE or node.process_mode == ProcessMode.ALWAYS:
                        node._process(delta)
                for child in node.get_children():
                    process_recursive(child)
            process_recursive(self.root)

        for _thread in self._threads:
            _thread.start()

        self._run_loop(self._frequency, precise_control=True, process_func=do_process, main_loop=True)

    def exit(self):
        """ 
        停止运行引擎

        目前退出引擎的方式是极不安全的，正常应该在所有线程和进程退出后再退出引擎
        """
        import sys
        import os

        
        info("正在退出引擎")
        info("Threading 模块正在运行的线程有： ")
        for _thread in threading.enumerate():
            info(f"{_thread.ident} {_thread.name}")

        info("Multiprocessing 模块正在运行的进程有： ")
        for _process in multiprocessing.active_children():
            info(f"{_process.pid} {_process.name}")

        info("当前使用强制退出，注意可能导致后续不稳定")

        os._exit(0)  # 强制退出，返回状态码为 0



        # self._shutdown.set()

    def _do_exit(self) -> None:
        pass
        # for _thread in self._threads:
        #     _thread.join()

        # self.engine_exit.emit()

        # time.sleep(1.0)
        # exit(0)
        
    def _run_loop(self, frequency, precise_control=False, process_func=None, main_loop=False):
        interval = 1.0 / frequency
        threshold = 0.03

        last_time = time.perf_counter()
        next_time = last_time
        first_frame = True

        if main_loop:
            self._start_timestamp = time.perf_counter_ns()

        while not self._shutdown.is_set():
            current_time = time.perf_counter()
            delta = current_time - last_time
            last_time = current_time

            if frequency == -1:
                if not first_frame and process_func:
                    if main_loop:
                        self._frame += 1
                        self._timestamp = time.perf_counter_ns() - self._start_timestamp
                    process_func(delta)
                else:
                    first_frame = False

            else:
                if not first_frame and process_func:
                    process_func(delta)
                    if main_loop:
                        self._frame += 1
                else:
                    first_frame = False

                if frequency != -1:
                    next_time += interval
                    sleep_time = next_time - time.perf_counter()

                    if precise_control:
                        if sleep_time > threshold:
                            time.sleep(sleep_time - threshold)

                        while time.perf_counter() < next_time:
                            pass

                    else:
                        if sleep_time > 0:
                            time.sleep(max(0, sleep_time))

                    if sleep_time < 0 and main_loop:
                        warning(f"当前帧{self._frame}耗时过长，超时：{-sleep_time*1000:.3f}ms")

        if main_loop:
            self._do_exit()

    def get_frame(self) -> int:
        """ 
        获取当前帧数 
        """
        return self._frame
    
    def get_timestamp(self) -> float:
        """ 
        获取当前时间戳，单位为微秒 
        """
        return self._timestamp
    
    def __del__(self):
        self.exit()