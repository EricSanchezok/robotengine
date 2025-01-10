"""

robot_link 是 robotengine 控制 ho 机器人的节点。

robot_link 与 机器人之间的通讯是自动的，在连接好设备并确定串口是正常开启后，会自动与机器人进行通讯并更新。

如果配置了 url robot_link 节点会自动发送机器人的状态 HoRobotState 到 url 指定的地址。

robot_link 会不断被动地接收机器人的状态并更新，但是不会主动向机器人发送数据。

使用 robot_link.update() 函数可以向机器人发送数据。

挂载 robot_link 节点后， _process() 的处理速度会显著受到影响，请酌情调整 engine 的运行频率。

"""

from robotengine.node import Node
from robotengine.serial_io import SerialIO, DeviceType, CheckSumType
from robotengine.tools import hex2str, warning, error
from robotengine.signal import Signal
from robotengine.timer import Timer
from typing import List, Tuple
from enum import Enum
import requests
import aiohttp
import asyncio
import threading
import time
import random

class HoMode(Enum):
    """ Ho 电机模态 """
    S = 0
    """ 停止 """
    I = 1
    """ 电流控制 """
    V = 2
    """ 速度控制 """
    P = 3
    """ 位置控制 """

class AlignState:
    """ 帧和时间戳对齐的状态数据 """
    def __init__(self, id: int, i: float, v: float, p: float, frame: int, timestamp: float):
        """ 初始化对齐状态数据 """
        self.id = id
        """ 电机 id """
        self.i: float = i
        """ 电流 """
        self.v: float = v
        """ 速度 """
        self.p: float = p
        """ 位置 """
        self.frame = frame
        """ 此状态数据对应的帧 """
        self.timestamp = timestamp
        """ 此状态数据对应的时间戳 """

    def to_dict(self):
        """ 转换为字典 """
        return {
            "id": self.id,
            "i": self.i,
            "v": self.v,
            "p": self.p,
            "frame": self.frame,
            "timestamp": self.timestamp
        }

    def __repr__(self):
        return f"AlignState(id={self.id}, i={round(self.i, 2)}, v={round(self.v, 2)}, p={round(self.p, 2)}, frame={self.frame}, timestamp={round(self.timestamp, 2)})"
    
class HoRobotState:
    """ Ho 机器人状态 """
    def __init__(self, states: List[AlignState]) -> None:
        """ 初始化 Ho 机器人状态 """
        self._states = states

    def get_state(self, id: int) -> AlignState:
        """ 获取指定 id 的状态 """
        for state in self._states:
            if state.id == id:
                return state
        return None
    
    def to_dict(self):
        """ 转换为字典 """
        return {
            "states": [state.to_dict() for state in self._states]
        }
    
    def __repr__(self):
        state_str = ""
        for state in self._states:
            state_str += str(state)
            if state != self._states[-1]:
                state_str += "\n"
        return f"HoRobotState(\n{state_str})"

class HoRobotLink(Node):
    """ Ho 机器人链接节点 """
    def __init__(self, name="HoRobotLink", buffer_capacity: int=1024, url=None, warn=True) -> None:
        """ 初始化 Ho 机器人链接节点 """
        super().__init__(name)
        self._data_length = 84
        self._receive_data = None
        self._url = url
        self._warn = warn
        self._shutdown = threading.Event()
        if self._url:
            self._pending_requests = []
            self._http_thread = threading.Thread(target=self._http_request)
            self._http_thread.start()

        self.buffer_capacity: int = buffer_capacity
        """ 存储状态数据的缓冲区的容量 """
        self.state_buffer: List[HoRobotState] = []
        """ 存储状态数据的缓冲区 """

        self.sio: SerialIO = SerialIO(name="SerialIO", device_type=DeviceType.STM32F407, checksum_type=CheckSumType.SUM16, header=[0x0D, 0x0A], warn=True, baudrate=1000000, timeout=1.0)
        """ 串口节点 RobotLink 会主动挂载一个已经配置好的串口节点 """
        self.add_child(self.sio)

        self.receive: Signal = Signal(bytes)
        """ 信号，当接收到数据时触发(无论是否通过校验和) """
        self.robot_state_update: Signal = Signal(HoRobotState)
        """ 信号，当接收到数据并成功通过校验和，将状态数据更新到信号参数中时触发 """

    def _ready(self) -> None:
        pass

    def _add_pending_request(self, robot_state: HoRobotState):
        self._pending_requests.append(robot_state)
        if len(self._pending_requests) > 32:
            self._pending_requests.pop(0)

    def _http_request(self):
        async def send_request(robot_state: HoRobotState) -> None:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self._url, json=robot_state.to_dict()) as response:
                        pass
                        # print(await response.json())
            except aiohttp.ClientError as e:
                if self._warn:
                    warning(f"{self.name} 向 {self._url} 发送请求时发生错误: {e}")
            except asyncio.TimeoutError:
                if self._warn:
                    warning(f"{self.name} 向 {self._url} 发送请求时发生超时错误")
            except Exception as e:
                if self._warn:
                    warning(f"{self.name} 向 {self._url} 发送请求时发生未知错误: {e}")

        while not self._shutdown.is_set():
            if self._pending_requests:
                robot_state = self._pending_requests.pop(0)
                asyncio.run(send_request(robot_state))
            time.sleep(0.01)

    def update(self, id: int, mode: HoMode, i: float, v: float, p: float) -> None:
        """ 向机器人发送数据 """
        data = bytes([id]) + bytes([mode.value]) + self._encode(p, 100.0, 4) + \
            self._encode(v, 100.0, 4) + self._encode(i, 100.0, 2)
        self.sio.transmit(data)

    def _process(self, delta) -> None:
        self._receive_data = self.sio.receive(self._data_length)
        if self._receive_data:
            if self.sio.check_sum(self._receive_data):
                states = []
                receive_data = self._receive_data[2:-2]

                id = 1
                for i in range(0, 80, 10):
                    _data = receive_data[i:i+10]
                    _p = self._decode(_data[0:4], 100.0, 4)
                    _v = self._decode(_data[4:8], 100.0, 4)
                    _i = self._decode(_data[8:10], 100.0, 2)

                    align_state = AlignState(id=id, i=_i, v=_v, p=_p, frame=self.engine.get_frame(), timestamp=self.engine.get_timestamp())
                    states.append(align_state)
                    id += 1

                robot_state = HoRobotState(states)
                self.state_buffer.append(robot_state)

                if len(self.state_buffer) > self.buffer_capacity:
                    self.state_buffer.pop(0)

                self.robot_state_update.emit(robot_state)
                if self._url:
                    self._add_pending_request(robot_state)
            else:
                if self._warn:
                    warning(f"{self.name} 接收数据 {hex2str(self._receive_data)} 校验和错误")
            self.receive.emit(self._receive_data)

    def _encode(self, value: float, scale_factor: float, byte_length: int) -> bytes:
        max_value = (1 << (8 * byte_length - 1))
        max_scaled_value = max_value / scale_factor

        if abs(value) >= max_scaled_value:
            raise ValueError(f"要编码的值 {round(value, 2)} 超出范围 [-{max_scaled_value}, {max_scaled_value}]")

        encoded_value = int(value * scale_factor) + max_value
        
        max_value_for_length = (1 << (8 * byte_length)) - 1
        if encoded_value > max_value_for_length:
            raise ValueError(f"编码值 {encoded_value} 超出了 {byte_length} 字节的最大值 {max_value_for_length}")

        byte_data = []
        for i in range(byte_length):
            byte_data.insert(0, encoded_value & 0xFF)
            encoded_value >>= 8

        return bytes(byte_data)

    def _decode(self, data: bytes, scale_factor: float, byte_length: int) -> float:
        if len(data) != byte_length:
            raise ValueError(f"数据长度 {len(data)} 与指定的字节长度 {byte_length} 不匹配")
        max_value = (1 << (8 * byte_length - 1))

        decoded_value = 0
        for i in range(byte_length):
            decoded_value <<= 8
            decoded_value |= data[i]
        
        decoded_value -= max_value

        return decoded_value / scale_factor




