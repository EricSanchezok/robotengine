"""

节点是 RobotEngine 的构建模块。它们可以被指定为另一个节点的子节点，从而形成树状排列。一个给定的节点可以包含任意数量的节点作为子节点，要求所有的兄弟节点（即该节点的直接子节点）的名字唯一。

当由节点组成的节点树被挂载到 Engine 中时，将会从子节点开始，依次执行每个节点的初始化程序 _init() 和 _ready()，注意 _init() 将会在 _ready() 之前被调用。

在节点的 _ready() 函数被调用后，将会触发节点中的 ready 信号。

节点可供覆写的弱定义函数有：

    def _init() -> None:
        # 初始化函数，在节点的 _ready() 函数被调用前被调用，尽量不要覆写此函数。
        pass

    def _ready() -> None:
        # 节点 _ready 函数，会在 _init() 之后被调用，可以在此函数中执行一些初始化操作。
        pass

    def _process(delta) -> None:
        # 节点 process 函数，会根据 Engine 中设置的 frequency 进行连续调用。
        pass

    def _input(event: InputEvent) -> None:
        # 节点 input 函数，会在接收到输入事件时被调用。
        pass

节点的 process 函数会根据 Engine 中设置的 frequency 进行连续调用，当节点的 process_mode 为 ProcessMode.PAUSABLE 时，当 Engine.paused 为 True 时，节点的 process 函数将不会被调用。

"""

from enum import Enum
from typing import List
from robotengine.tools import warning, error
from robotengine.signal import Signal


class ProcessMode(Enum):
    """ 节点的process模式，PAUSABLE为默认模式 """
    PAUSABLE = 0
    """ 当 Engine.paused 为 True 时，节点的 process 函数将不会被调用 """
    WHEN_PAUSED = 1
    """ 只有当 Engine.paused 为 True 时，节点的 process 函数才会被调用 """
    ALWAYS = 2
    """ 节点的 process 函数将始终被调用 """
    DISABLED = 3
    """ 节点的 process 函数将永远不会被调用 """

class Node:
    """ Node 基类 """
    from robotengine.input import InputEvent

    def __init__(self, name="Node"):
        """ 初始化节点， 需要指定节点名称 """
        self.name = name
        """ 节点名称 """
        self.owner = None
        """
        节点的所有者

        注意：owner的指定与节点的创建顺序有关，例如：

            A = Node("A")
            B = Node("B")
            C = Node("C")
            D = Node("D")

            A.add_child(B)
            A.add_child(C)
            B.add_child(D)

        此时，A的子节点为B、C，B的子节点为D，B、C、D的owner均为A。

        而如果继续添加节点：

            E = Node("E")
            E.add_child(A)

        此时，E的子节点为A，A的owner为E，但是B、C、D的owner仍然为A。
        """
        self._children = []
        self._parent = None

        # 全局属性
        from robotengine.engine import Engine
        from robotengine.input import Input

        self.engine: Engine = None
        """ 节点的 Engine 实例 """
        self.input: Input = None
        """ 节点的 Input 实例 """

        self.process_mode: ProcessMode = ProcessMode.PAUSABLE
        """ 节点的process模式 """

        # 信号
        self.ready: Signal = Signal()
        """ 信号，节点 _ready 执行结束后触发 """

    def add_child(self, child_node):
        """ 添加子节点 """
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
        """ 移除子节点 """
        if child_node in self._children:
            self._children.remove(child_node)
            child_node._parent = None  # 解除 _parent 绑定
        else:
            warning(f"{self.name}：{child_node.name} 并未被找到，未执行移除操作")

    def _update(self, delta) -> None:
        """ 引擎内部的节点更新函数，会以很低的频率调用 """
        pass

    def _timer(self, delta) -> None:
        """ 引擎内部的定时器更新函数，负责 Timer 相关的更新 """
        pass

    def _init(self) -> None:
        """ 初始化节点，会在 _ready() 之前被调用，尽量不要覆写此函数 """
        pass
    
    def _ready(self) -> None:
        """ 节点 _ready 函数，会在 _init() 之后被调用，可以在此函数中执行一些初始化操作 """
        pass

    def _ready_execute(self) -> None:
        self._ready()
        self.ready.emit()

    def _process(self, delta) -> None:
        """ 节点 process 函数，会根据 Engine 中设置的 frequency 进行连续调用 """
        pass

    def _input(self, event: InputEvent) -> None:
        """ 节点 input 函数，会在接收到输入事件时被调用 """
        pass

    def get_child(self, name) -> "Node":
        """ 通过节点名称获取子节点 """
        for child in self._children:
            if child.name == name:
                return child
        return None
    
    def get_children(self) -> List["Node"]:
        """ 获取所有子节点 """
        return self._children
    
    def get_parent(self) -> "Node":
        """ 获取父节点 """
        return self._parent
    
    def rbprint(self, str):
        print(f"[{self.engine.get_frame()}] {str}")

    def __repr__(self):
        return f"{self.name}"
