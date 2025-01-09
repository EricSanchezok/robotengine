from robotengine.node import Node
from robotengine.serial_io import SerialIO, DeviceType, CheckSumType
from robotengine.tools import hex2str
from robotengine.signal import Signal
from typing import List

class RobotState:
    def __init__(self, frame: int, angles: List[float]):
        self.frame = frame
        self.angles = angles

    def __repr__(self):
        return f"RobotState(frame={self.frame}, angles={self.angles})"
    
class RobotLink(Node):
    def __init__(self, name="RobotLink", buffer_capacity: int=1024):
        super().__init__(name)
        self._data_length = 36
        self._receive_data = None

        self.buffer_capacity = buffer_capacity
        self.state_buffer = []

        self.sio = SerialIO(name="SerialIO",
                           device_type=DeviceType.STM32F407,
                           checksum_type=CheckSumType.SUM16,
                           header=[0x0D, 0x0A],
                           baudrate=115200,
                           timeout=1.0)
        self.add_child(self.sio)

        self.receive = Signal()
        self.state_update = Signal(RobotState)

    def _process(self, delta) -> None:
        self._receive_data = self.sio.receive(self._data_length)
        if self._receive_data:
            if self.sio.check_sum(self._receive_data):
                data = self._receive_data[2:-2]

                angles = [
                    (data[i] << 24 | data[i+1] << 16 | data[i+2] << 8 | data[i+3]) / 1000.0
                    for i in range(0, len(data), 4)  # 每4个字节为一个角度值
                ]

                robot_state = RobotState(self.engine.get_frame(), angles)
                self.state_buffer.append(robot_state)

                if len(self.state_buffer) > self.buffer_capacity:
                    self.state_buffer.pop(0)

                self.state_update.emit(robot_state)

            self.receive.emit()
