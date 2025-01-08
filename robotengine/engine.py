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
        self._interval = 1 / frequency  # 每次循环间隔时间

        self._running = False  # 引擎运行状态
        self.paused = False  # 引擎暂停状态
        self._frame = 0  # 帧数计数器

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

    def initialize(self):
        """从叶子节点到根节点依次调用 _init 和 _ready"""
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
            node._ready()  # 当前节点准备完成

        init_recursive(self.root)
        ready_recursive(self.root)

    def _update(self):
        """每帧调用 _update，从根节点递归调用"""
        from.node import Node
        def update_recursive(node: Node):
            for child in node.get_children():
                update_recursive(child)  # 先更新子节点
            node._update()  # 当前节点的更新逻辑

        while not self._shutdown.is_set():
            update_recursive(self.root)
            time.sleep(0.2)

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
        """每帧调用 _process，从根节点递归调用"""
        from .node import Node
        def process_recursive(node: Node):
            if self.paused:
                if node.process_mode == ProcessMode.WHEN_PAUSED or node.process_mode == ProcessMode.ALWAYS:
                    node._process(delta)
            else:
                if node.process_mode == ProcessMode.PAUSABLE or node.process_mode == ProcessMode.ALWAYS:
                    node._process(delta)
            for child in node.get_children():
                process_recursive(child)  # 子节点的处理逻辑

        process_recursive(self.root)

    def run(self):
        """主循环"""
        self._running = True
        self._frame = 0
        threshold = 0.03

        # 记录循环开始的时间
        last_time = time.perf_counter()   
        next_time = last_time  # 记录下一次期望的执行时间

        first_frame = True 

        while self._running:
            current_time = time.perf_counter()  # 当前帧开始的时间
            delta = current_time - last_time  # 计算本帧与上一帧的时间差
            last_time = current_time  # 更新 last_time 为当前时间
            
            if not first_frame:
                self._process(delta)
                self._frame += 1
            else:
                first_frame = False  # 标记为非第一帧

            next_time += self._interval
            sleep_time = next_time - time.perf_counter()

            if sleep_time > threshold:
                time.sleep(sleep_time - threshold)  # 休眠大部分时间，留下一小部分时间进行精确控制

            # 空循环，等待剩余的部分来精确定时
            while time.perf_counter() < next_time:
                pass  # 等待直到达到下一个预期时间

            # 如果任务执行时间超过了间隔，跳过休眠
            if sleep_time <= 0:
                print(f"WARNING: Skipping sleep. Frame took too long. Delta: {delta:.5f}s")

    def stop(self):
        """停止引擎"""
        self._shutdown.set()
        self._running = False
        
    def get_frame(self) -> int:
        """获取当前帧数"""
        return self._frame

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