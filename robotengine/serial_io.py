from .node import Node
import serial.tools.list_ports
import serial
from enum import Enum
import random
from robotengine.tools import hex2str, warning, error
import zlib

class DeviceType(Enum):
    STM32F407 = 0
    ARDUINO_MEGA2560 = 1

class CheckSumType(Enum):
    NONE = 0
    SUM8 = 1
    SUM16 = 2
    XOR8 = 3
    XOR16 = 4
    CRC8 = 5
    CRC16 = 6

checksum_length_map = {
        CheckSumType.SUM8: 1,
        CheckSumType.SUM16: 2,
        CheckSumType.XOR8: 1,
        CheckSumType.XOR16: 2,
        CheckSumType.CRC8: 1,
        CheckSumType.CRC16: 2
    }

class SerialIO(Node):
    def __init__(self, name="SerialIO", device_type=DeviceType.STM32F407, checksum_type=CheckSumType.NONE, header=[], baudrate=115200, timeout=1.0):
        super().__init__(name)
        self.device_type = device_type
        self.checksum_type = checksum_type
        self.header = header
        self.device = None
        self.serial: serial.Serial = None
        self.baudrate = baudrate
        self.timeout = timeout

        self._initialize()
        if self.device is None:
            warning(f"节点 {self.name} 初始化时未检测到 {self.device_type} 设备，将在内部更新中继续尝试")

    def _update(self, delta) -> None:
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
    
    def _get_check_sum(self, data: bytes) -> bytes:
        if self.checksum_type == CheckSumType.SUM8:
            check_sum = sum(data) & 0xFF
            return bytes([check_sum])
        elif self.checksum_type == CheckSumType.SUM16:
            check_sum = sum(data) & 0xFFFF
            return check_sum.to_bytes(2, byteorder='big')
        elif self.checksum_type == CheckSumType.XOR8:
            check_sum = 0
            for byte in data:
                check_sum ^= byte
            return bytes([check_sum])
        elif self.checksum_type == CheckSumType.XOR16:
            check_sum = 0
            for byte in data:
                check_sum ^= byte
            return check_sum.to_bytes(2, byteorder='big')
        elif self.checksum_type == CheckSumType.CRC8:
            crc = 0x00
            polynomial = 0x07
            for byte in data:
                crc ^= byte
                for _ in range(8):
                    if crc & 0x80:
                        crc = (crc << 1) ^ polynomial
                    else:
                        crc <<= 1
                    crc &= 0xFF
            return bytes([crc])
        elif self.checksum_type == CheckSumType.CRC16:
            crc = 0xFFFF
            polynomial = 0x8005
            for byte in data:
                crc ^= byte
                for _ in range(8):
                    if crc & 0x0001:
                        crc = (crc >> 1) ^ polynomial
                    else:
                        crc >>= 1  # 否则仅右移
            return crc.to_bytes(2, byteorder='big')
        else:
            raise ValueError("无效的校验和类型")
            
    def _add_header(self, data: bytes) -> bytes:
        return bytes(self.header) + data
    
    def random_bytes(self, length: int) -> bytes:
        return bytes([random.randint(0, 255) for _ in range(length)])
    
    def fixed_bytes(self, byte: int, length: int) -> bytes:
        return bytes([byte for _ in range(length)])
    
    def transmit(self, data: bytes) -> bytes:
        if self.serial is None:
            warning(f"节点 {self.name} 串口未初始化，无法发送数据")
            return
        if self.checksum_type !=CheckSumType.NONE:
            data += self._get_check_sum(data)
        if self.header:
            data = self._add_header(data)
        self.serial.write(data)
        return data

    def receive(self, len: int) -> bytes:
        if self.serial is None:
            warning(f"节点 {self.name} 串口未初始化，无法接收数据")
            return
        if self.serial.in_waiting >= len:
            return self.serial.read(len)
        else:
            return None
        
    def check_sum(self, data: bytes) -> bool:
        checksum_length = checksum_length_map.get(self.checksum_type)
        if checksum_length is None:
            raise ValueError("无效的校验和类型，无法进行校验")

        data_to_check = data[len(self.header):-checksum_length]
        expected_checksum = data[-checksum_length:]
        calculated_checksum = self._get_check_sum(data_to_check)
        # print(f"data: {hex2str(data)}")
        # print(f"expected_checksum: {hex2str(expected_checksum)}, calculated_checksum: {hex2str(calculated_checksum)}")
        return calculated_checksum == expected_checksum

    def __del__(self):
        if self.serial:
            self.serial.close()