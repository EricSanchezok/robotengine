from robotengine.node import Node
from robotengine.serial_io import SerialIO, DeviceType, CheckSumType
import threading
import time
from robotengine.tools import hex_to_str

class RobotLink(Node):
    def __init__(self, name="RobotLink"):
        super().__init__(name)
        self.sio = SerialIO(name="SerialIO",
                           device_type=DeviceType.STM32F407,
                           checksum_type=CheckSumType.SUM16,
                           header=[0x0D, 0x0A],
                           baudrate=115200,
                           timeout=1.0)
        
        self.add_child(self.sio)

        self._data_length = 36

        self._receive_thread = threading.Thread(target=self._receive, daemon=True)
        self._receive_thread.start()

        self._receive_data = None

    def _receive(self):
        while True:
            self._receive_data = self.sio.receive(self._data_length)
            if self._receive_data:
                print("RX: ", hex_to_str(self._receive_data))
            time.sleep(0.01)

    def _process(self, delta) -> None:
        # data = self.sio.transmit(self.sio.fixed_bytes(0x0A, 32))
        data = self.sio.transmit(self.sio.random_bytes(32))
        print("TX: ", hex_to_str(data))
