import threading
import time
from enum import Enum
from .input import Input, GamepadListener
from .node import ProcessMode

class InputDevice(Enum):
    KEYBOARD = 0
    MOUSE = 1
    GAMEPAD = 2
class Engine:
    from .node import Node
    def __init__(self, root: Node, frequency=30, input_devices=[]):
        self.root = root  # 根节点
        self._frequency = frequency  # 每秒运行的帧数

        self.paused = False  # 引擎暂停状态
        self._frame = 0  # 帧数计数器
        self._timestamp = 0.0  # 时间戳

        self.input = Input()

        self.initialize()  # 初始化引擎

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

    def initialize(self):
        from .node import Node
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
        from.node import Node
        def update_recursive(node: Node, delta):
            for child in node.get_children():
                update_recursive(child, delta)
            node._update(delta)
        update_recursive(self.root, delta)

    def _update(self):
        self.run_loop(1, precise_control=False, process_func=self._process_update)

    def _process_timer(self, delta):
        from.node import Node
        def timer_recursive(node: Node, delta):
            for child in node.get_children():
                timer_recursive(child, delta)  # 先更新子节点
            node._timer(delta)  # 当前节点的更新逻辑
        timer_recursive(self.root, delta)

    def _timer(self):
        self.run_loop(30, precise_control=False, process_func=self._process_timer)
            
    def _input(self):
        from .node import Node
        from .input import InputEvent
        def input_recursive(node: Node, event: InputEvent):
            for child in node.get_children():
                input_recursive(child, event)  # 先处理子节点
            node._input(event)  # 当前节点的处理逻辑

        while not self._shutdown.is_set():
            if self._gamepad_listener:
                for _gamepad_event in self._gamepad_listener.listen():
                    self.input.update(_gamepad_event)

                    input_recursive(self.root, _gamepad_event)

    def _process(self, delta):
        from .node import Node
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
        self.run_loop(self._frequency, precise_control=True, process_func=self._process, main_loop=True)

    def stop(self):
        self._shutdown.set()

    def run_loop(self, frequency, precise_control=False, process_func=None, main_loop=False):
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
                print(f"WARNING: Skipping sleep. Frame took too long. Delta: {delta:.5f}s")

            
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