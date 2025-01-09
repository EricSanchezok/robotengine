from enum import Enum
from robotengine import Node, ProcessMode
from robotengine import StateMachine
from robotengine import SerialIO, DeviceType, CheckSumType
from robotengine import Engine
from robotengine import Timer
from robotengine import InputEvent
from robotengine import RobotLink, RobotState

class State(Enum):
    IDLE = 0
    THINKING = 1

class Robot(Node):
    def __init__(self, name="Robot"):
        super().__init__(name)
        self.state_machine = StateMachine(name="StateMachine", initial_state=State.IDLE)
        self.add_child(self.state_machine)

        self.robotlink = RobotLink()
        self.add_child(self.robotlink)

        self.robotlink.state_update.connect(self._on_state_update)

    def _ready(self) -> None:
        pass

    def _input(self, event: InputEvent) -> None:
        pass

    def _on_state_update(self, state: RobotState) -> None:
        self.rbprint(f"Buffer Length: {len(self.robotlink.state_buffer)} RobotState: {state}")
        
    def tick(self, state: State, delta: float) -> None:
        # if self.engine.get_frame() % 5 == 0:
        #     print(f"[{self.engine.get_frame()}] {state}")
        #     self.robotlink.sio.transmit(self.robotlink.sio.random_bytes(32))
            
        if state == State.IDLE:
            pass

        elif state == State.THINKING:
            pass

    def get_next_state(self, state: State) -> State:
        if state == State.IDLE:
            if self.state_machine.state_time >= 999.0:
                return State.THINKING

        elif state == State.THINKING:
            if self.state_machine.state_time >= 3.0:
                return State.IDLE
        
        return StateMachine.KEEP_CURRENT

    def transition_state(self, from_state: State, to_state: State) -> None:
        print(f"[{self.engine.get_frame()}] {from_state if from_state is not None else 'START'} -> {to_state}")


if __name__ == '__main__':
    root = Node("Root")
    robot = Robot()
    root.add_child(robot)

    engine = Engine(root, frequency=1, input_devices=[])
    engine.print_tree()
    engine.run()