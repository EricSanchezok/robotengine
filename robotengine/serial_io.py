from .node import Node
import serial.tools.list_ports
import serial
from enum import Enum
import random
from .tools import hex_to_str, warning, error

class DeviceType(Enum):
    STM32F407 = 0
    ARDUINO_MEGA2560 = 1

class SerialIO(Node):
    def __init__(self, name="SerialIO", device_type=DeviceType.STM32F407, baudrate=115200, timeout=1.0):
        super().__init__(name)
        self.device_type = device_type
        self.device = None
        self.serial: serial.Serial = None
        self.baudrate = baudrate
        self.timeout = timeout

        self._initialize()
        if self.device is None:
            warning(f"节点 {self.name} 初始化时未检测到 {self.device_type} 设备，将在内部更新中继续尝试")

    def _update(self) -> None:
        if self.device is None:
            self._initialize()
            return
        
    def _initialize(self):
        self.device = self._find_device()
        if self.device:
            self.serial = serial.Serial(self.device, self.baudrate, timeout=self.timeout)

    def _find_device(self):
        if self.device_type == DeviceType.STM32F407:
            target_vid = 0x1A86
            target_pid = 0x7523
        elif self.device_type == DeviceType.ARDUINO_MEGA2560:
            target_vid = 0x2341
            target_pid = 0x0043

        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid == target_vid and port.pid == target_pid:
                return port.device
        return None
    
    def _add_check_sum(self, data: bytes) -> bytes:
        check_sum = sum(data) & 0xFF
        return data + bytes([check_sum])
    
    def _add_header(self, data: bytes) -> bytes:
        return bytes([0x0D, 0x0A]) + data
    
    def random_bytes(self, length: int) -> bytes:
        return bytes([random.randint(0, 255) for _ in range(length)])
    
    def transmit(self, data: bytes):
        if self.serial is None:
            warning(f"节点 {self.name} 串口未初始化，无法发送数据")
            return
        data = self.add_header(data)
        data = self.add_check_sum(data)
        self.serial.write(data)

    def __del__(self):
        if self.serial:
            print("Closing serial port")
            self.serial.close()