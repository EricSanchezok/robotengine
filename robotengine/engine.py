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
from robotengine.tools import warning, error

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
    def __init__(self, root: Node, frequency: float=240, input_devices: InputDevice=[]):
        """
        初始化引擎

        参数:

            root (Node): 根节点

            frequency (int, optional): 影响所有节点的 _process 函数的调用频率。默认值为 240。

            input_devices (list, optional): 输入设备列表，当为空时，节点的 _input() 函数将不会被调用。默认值为 []。
        """
        self.root = root
        """ 根节点 """
        self.paused = False
        """ 是否暂停 """

        self._frequency = frequency
        self._frame = 0
        self._timestamp = 0.0

        self._time_frequency = 30

        self.input = Input()
        """ 输入类， 在 Engine 初始化完成后，每个 Node 都可以通过 self.input 来访问输入类 """

        self._initialize()

        self._shutdown = threading.Event()
        if input_devices:
            if InputDevice.GAMEPAD in input_devices:
                self._gamepad_listener = GamepadListener()

            self._input_thread = threading.Thread(target=self._input, daemon=True)
            self._input_thread.start()

        self._update_thread = threading.Thread(target=self._update, daemon=True)
        self._update_thread.start()

        self._timer_thread = threading.Thread(target=self._timer, daemon=True)
        self._timer_thread.start()

    def _initialize(self):
        from robotengine.node import Node
        def init_recursive(node: Node):
            for child in node.get_children():
                init_recursive(child)  # 先初始化子节点
            
            node.engine = self  # 设置引擎引用
            node.input = self.input  # 设置输入引用
            
            node._init()  # 当前节点初始化

        def ready_recursive(node: Node):
            for child in node.get_children():
                ready_recursive(child)  # 子节点准备完成
            node._ready_execute()

        init_recursive(self.root)
        ready_recursive(self.root)

    def _process_update(self, delta):
        from robotengine.node import Node
        def update_recursive(node: Node, delta):
            for child in node.get_children():
                update_recursive(child, delta)
            node._update(delta)
        update_recursive(self.root, delta)

    def _update(self):
        self._run_loop(1, precise_control=False, process_func=self._process_update)

    def _process_timer(self, delta):
        from robotengine.node import Node
        def timer_recursive(node: Node, delta):
            for child in node.get_children():
                timer_recursive(child, delta)
            node._timer(delta)
        timer_recursive(self.root, delta)

    def _timer(self):
        self._run_loop(self._time_frequency, precise_control=False, process_func=self._process_timer)
            
    def _input(self):
        from robotengine.node import Node
        from robotengine.input import InputEvent
        def input_recursive(node: Node, event: InputEvent):
            for child in node.get_children():
                input_recursive(child, event)
            node._input(event)

        while not self._shutdown.is_set():
            if self._gamepad_listener:
                for _gamepad_event in self._gamepad_listener.listen():
                    self.input.update(_gamepad_event)

                    input_recursive(self.root, _gamepad_event)

    def _process(self, delta):
        from robotengine.node import Node
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

    def run(self):
        """ 开始运行引擎 """
        self._run_loop(self._frequency, precise_control=True, process_func=self._process, main_loop=True)

    def stop(self):
        """ 停止运行引擎 """
        self._shutdown.set()

    def _run_loop(self, frequency, precise_control=False, process_func=None, main_loop=False):
        interval = 1.0 / frequency
        threshold = 0.03

        last_time = time.perf_counter()
        next_time = last_time
        first_frame = True

        while not self._shutdown.is_set():
            current_time = time.perf_counter()
            delta = current_time - last_time
            last_time = current_time

            if not first_frame and process_func:
                process_func(delta)
                if main_loop:
                    self._frame += 1
                    self._timestamp += delta
            else:
                first_frame = False

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

            if sleep_time <= 0 and main_loop:
                warning(f"当前帧{self._frame}耗时过长，耗时{delta:.5f}s")

            
    def get_frame(self) -> int:
        """获取当前帧数"""
        return self._frame
    
    def get_timestamp(self) -> float:
        """获取当前时间戳"""
        return self._timestamp

    def print_tree(self):
        """打印节点树"""
        from .node import Node
        def print_recursive(node: Node, prefix="", is_last=False, is_root=False):
            if is_root:
                print(f"{node}")  # 根节点
            else:
                if is_last:
                    print(f"{prefix}└── {node}")  # 最后一个子节点
                else:
                    print(f"{prefix}├── {node}")  # 其他子节点

            for i, child in enumerate(node.get_children()):
                is_last_child = (i == len(node.get_children()) - 1)
                print_recursive(child, prefix + "    ", is_last=is_last_child, is_root=False)

        print_recursive(self.root, is_last=False, is_root=True)