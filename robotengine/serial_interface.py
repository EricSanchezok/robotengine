from node import Node
import serial.tools.list_ports
import serial
from enum import Enum
import random
import tools

class DeviceType(Enum):
    STM32F407 = 0
    ARDUINO_MEGA2560 = 1

class SerialInterface(Node):
    def __init__(self, name="SerialInterface", device_type=DeviceType.STM32F407, baudrate=115200, timeout=1.0):
        super().__init__(name)
        self.device_type = device_type
        self.device = None
        self.serial: serial.Serial = None
        self.baudrate = baudrate
        self.timeout = timeout

    def _ready(self) -> None:
        self.initialize()

    def _process(self, delta: float) -> None:
        if self.device is None:
            self.initialize()
            return
        
        # if self.serial.in_waiting >= 10:
        #     data = self.serial.read(10)
        #     print("Receiving:")
        #     tools.print_hex(data)

        # 生成32个随机字节（0-255之间的整数）
        random_bytes = bytes([random.randint(0, 255) for _ in range(8)])
        
        message = self.add_header(random_bytes)
        message = self.add_check_sum(message)

        self.transmit(message)

        print("Transmitting:")
        tools.print_hex(message)
        
    def initialize(self):
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
                print(f"Found {self.device_type} device: {port.device}")
                return port.device
        return None
    
    def add_check_sum(self, data: bytes) -> bytes:
        check_sum = sum(data) & 0xFF
        return data + bytes([check_sum])
    
    def add_header(self, data: bytes) -> bytes:
        return bytes([0x3E]) + data
    
    def transmit(self, data: bytes):
        data = self.add_header(data)
        data = self.add_check_sum(data)
        self.serial.write(data)

    def __del__(self):
        if self.serial:
            print("Closing serial port")
            self.serial.close()