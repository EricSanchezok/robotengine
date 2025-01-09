from enum import Enum
from typing import List
from .tools import warning, error
from .signal import Signal
class ProcessMode(Enum):
    PAUSABLE = 0
    WHEN_PAUSED = 1
    ALWAYS = 2
    DISABLED = 3

class Node:
    from .input import InputEvent
    
    def __init__(self, name="Node"):
        self.name = name         # 节点名称
        self._children = []       # 子节点列表
        self._parent = None       # 父节点，初始为 None
        self.owner = None

        # 全局属性
        from .engine import Engine
        from .input import Input
        self.engine: Engine = None
        self.input: Input = None

        self.process_mode = ProcessMode.PAUSABLE

        # 信号
        self.ready = Signal()

    def add_child(self, child_node):
        if child_node._parent is not None:
            error(f"{self.name}：{child_node.name} 已经有父节点！")
            return
        for child in self._children:
            if child.name == child_node.name:
                error(f"节点 {self.name} 已经有同名子节点{child_node.name} ！")
                return

        child_node._parent = self  # 设置子节点的 _parent 属性
        if self.owner is not None:
            child_node.owner = self.owner
        else:
            child_node.owner = self

        self._children.append(child_node)

    def remove_child(self, child_node):
        if child_node in self._children:
            self._children.remove(child_node)
            child_node._parent = None  # 解除 _parent 绑定
        else:
            warning(f"{self.name}：{child_node.name} 并未被找到，未执行移除操作")

    def _update(self, delta) -> None:
        pass

    def _timer(self, delta) -> None:
        pass

    def _init(self) -> None:
        pass
    
    def _ready(self) -> None:
        pass

    def _ready_execute(self) -> None:
        self._ready()
        self.ready.emit()

    def _process(self, delta) -> None:
        pass

    def _input(self, event: InputEvent) -> None:
        pass

    def get_child(self, name) -> "Node":
        for child in self._children:
            if child.name == name:
                return child
        return None
    
    def get_children(self) -> List["Node"]:
        return self._children
    
    def get_parent(self) -> "Node":
        return self._parent

    def __repr__(self):
        return f"{self.name}"
