from enum import Enum
from typing import List

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

    def add_child(self, child_node):
        if child_node._parent is not None:
            raise ValueError(f"{child_node.name} already has a parent!")
        child_node._parent = self  # 设置子节点的 _parent 属性
        if self.owner is not None:
            child_node.owner = self.owner
        else:
            child_node.owner = self

        self._children.append(child_node)
        # print(f"{self.name}: Added child {child_node.name}")

    def remove_child(self, child_node):
        if child_node in self._children:
            self._children.remove(child_node)
            child_node._parent = None  # 解除 _parent 绑定
            # print(f"{self.name}: Removed child {child_node.name}")
        else:
            raise ValueError(f"{child_node.name} is not a child of {self.name}!")

    def _init(self) -> None:
        pass

    def _ready(self) -> None:
        pass

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
