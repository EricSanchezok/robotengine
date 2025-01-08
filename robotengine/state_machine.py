from .node import Node
import time
from .tools import error

class StateMachine(Node):
    KEEP_CURRENT = -1

    def __init__(self, initial_state, name="StateMachine"):
        super().__init__(name)
        self.state_time = 0.0
        self.current_state = initial_state

        self.first = True
         
    def _process(self, delta: float) -> None:
        start_transition_time = time.time()
        while True:
            if self.first:
                self.first = False
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