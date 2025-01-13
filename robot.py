from enum import Enum
from robotengine import Node, ProcessMode
from robotengine import StateMachine
from robotengine import SerialIO, DeviceType, CheckSumType
from robotengine import Engine
from robotengine import Timer
from robotengine import InputEvent
from robotengine import HoLink, HoState, HoMode, AlignState, HoManual

class State(Enum):
    IDLE = 0
    MANUAL = 1

class Robot(Node):
    def __init__(self, name="Robot", warn=True):
        super().__init__(name)
        self.state_machine = StateMachine(name="StateMachine", initial_state=State.IDLE)
        self.add_child(self.state_machine)

        url = 'http://127.0.0.1:7777/data'
        self.robotlink = HoLink(url=url, warn=warn)
        self.add_child(self.robotlink)

        self.ho_manual = HoManual(self.robotlink)
        self.add_child(self.ho_manual)

    def _ready(self) -> None:
        pass

    def _input(self, event: InputEvent) -> None:
        if self.ho_manual.is_running():
            return
        
        if event.is_action_pressed("BACK"):
            self.engine.exit()

    def tick(self, state: State, delta: float) -> None:  
        if state == State.IDLE:
            pass

        elif state == State.MANUAL:
            pass

    def get_next_state(self, state: State) -> State:
        if state == State.IDLE:
            if self.input.is_action_pressed("A") and self.input.is_action_pressed("Y"):
                self.input.flush_action("A")
                self.input.flush_action("Y")
                return State.MANUAL

        elif state == State.MANUAL:
            if self.input.is_action_pressed("A") and self.input.is_action_pressed("Y"):
                self.input.flush_action("A")
                self.input.flush_action("Y")
                return State.IDLE
        
        return StateMachine.KEEP_CURRENT

    def transition_state(self, from_state: State, to_state: State) -> None:
        self.state_machine.t_info(from_state, to_state)

        if from_state == State.IDLE:
            pass
        elif from_state == State.MANUAL:
            self.ho_manual.exit()


        if to_state == State.IDLE:
            pass
        elif to_state == State.MANUAL:
            self.ho_manual.enter()

if __name__ == '__main__':
    root = Node("Root")
    
    robot = Robot()
    root.add_child(robot)

    engine = Engine(root, frequency=180, input_devices=[])
    engine.print_tree()
    engine.run()