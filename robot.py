from enum import Enum
from robotengine import Node, ProcessMode
from robotengine import StateMachine
from robotengine import SerialIO, DeviceType, CheckSumType, ReadMode
from robotengine import Engine
from robotengine import Timer
from robotengine import InputEvent
from robotengine import HoLink, HoState, HoMode, AlignState

class State(Enum):
    IDLE = 0
    THINKING = 1

class Robot(Node):
    def __init__(self, name="Robot", warn=True):
        super().__init__(name)
        self.state_machine = StateMachine(name="StateMachine", initial_state=State.IDLE)
        self.add_child(self.state_machine)

        self.robotlink = HoLink(url='http://127.0.0.1:7777/data', read_mode=ReadMode.SINGLE, warn=warn)
        self.add_child(self.robotlink)

        self.robotlink.robot_state_update.connect(self._on_robot_state_update)

    def _ready(self) -> None:
        pass

    def _input(self, event: InputEvent) -> None:
        if event.is_action_pressed("BACK"):
            self.engine.exit()

    def _on_robot_state_update(self, robot_state: HoState) -> None:
        pass
        # self.robotlink.update(2, HoMode.V, 0.8, -360.0, 0.0)
        # self.robotlink.update(3, HoMode.V, 0.8, 360.0, 0.0)

    def tick(self, state: State, delta: float) -> None:    
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

    engine = Engine(root, frequency=180, input_devices=[])
    engine.print_tree()
    engine.run()