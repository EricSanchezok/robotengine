"""

state_machine 是 robotengine 控制 owner 复杂状态的节点。

需要在 owner 中实现以下函数：

    # 状态机每帧更新
    def tick(self, state, delta):
        pass

    # 状态机切换的条件
    def get_next_state(self, state):
        pass
    
    # 状态机切换时的回调
    def transition_state(self, from, to):
        pass
    
实现良好的状态机需要注意防止产生状态切换的死循环

"""

from robotengine.node import Node
import time
from robotengine.tools import error

class StateMachine(Node):
    """ 状态机节点 """
    KEEP_CURRENT = -1
    """ 维持当前状态的状态码 """

    def __init__(self, initial_state, name="StateMachine"):
        """ 
        初始化状态机， 需要传递初始状态，通常是枚举类型 
        
            :param initial_state: 初始状态
            :param name: 节点名称
        """
        super().__init__(name)
        self.state_time = 0.0
        """ 当前状态持续的时间 """
        self.current_state = initial_state
        """ 状态机的当前状态 """
        self.first_tick = True
        """ 是否是第一帧（刚初始化StateMachine时） """
        self.freeze = False
        """ 是否冻结状态机 """
         
    def _process(self, delta: float) -> None:
        if self.freeze:
            return
        
        start_transition_time = time.time()
        while True:
            if self.first_tick:
                self.first_tick = False
                self.owner.transition_state(None, self.current_state)

            next = self.owner.get_next_state(self.current_state)
            if next == StateMachine.KEEP_CURRENT:
                break
            self.owner.transition_state(self.current_state, next)
            self.current_state = next
            self.state_time = 0.0

            if time.time() - start_transition_time > 1.0:
                error(f"{self.owner.name} state_machine {self.current_state} transition timeout")

        self.owner.tick(self.current_state, delta)
        self.state_time += delta

    def t_info(self, from_state, to_state) -> None:
        self.rbprint(f"{from_state if from_state is not None else 'START'} -> {to_state} from:{self.name} ")
