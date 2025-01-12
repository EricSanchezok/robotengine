"""

ho_robot 是 robotengine 控制 ho 机器人的节点。

ho_robot 与 机器人之间的通讯是自动的，在连接好设备并确定串口是正常开启后，会自动与机器人进行通讯并更新。

如果配置了 url ho_robot 节点会自动发送机器人的状态 HoState 到 url 指定的地址。

ho_robot 会不断被动地接收机器人的状态并更新，但是不会主动向机器人发送数据。

使用 ho_robot.update() 函数可以向机器人发送数据。

挂载 ho_robot 节点后，_process()的处理速度会显著受到影响，请酌情调整 engine 的运行频率。

"""

from robotengine.node import Node
from robotengine.serial_io import SerialIO, DeviceType, CheckSumType
from robotengine.tools import hex2str, warning, error, info
from robotengine.signal import Signal
from robotengine.timer import Timer
from typing import List, Tuple
from enum import Enum
import requests
import threading
import time
import random
import multiprocessing
import tkinter as tk
from ttkbootstrap import ttk
import ttkbootstrap as ttkb
from fastapi import FastAPI, Request
import uvicorn
from urllib.parse import urlparse
import copy

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
    def __init__(self, id: int, i: float, v: float, p: float, frame: int, timestamp: float) -> None:
        """ 
        初始化对齐状态数据

            :param id: 电机 id
            :param i: 电流
            :param v: 速度
            :param p: 位置
            :param frame: 当前帧
            :param timestamp: 当前时间戳 
        """
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
    
class HoState:
    """ Ho 机器人状态 """
    def __init__(self, states: List[AlignState], random_state=False) -> None:
        """ 
        初始化 Ho 机器人状态

            :param states: 帧和时间戳对齐的状态数据列表
            :param random_state: 是否随机生成状态数据
        """
        if not random_state:
            self._states = states
        else:
            self._states = []
            for i in range(1, 9):
                self._states.append(AlignState(i, random.uniform(-1.0, 1.0), random.uniform(-360.0, 360.0), random.uniform(-1000.0, 1000.0), 0, 0.0))

    def get_state(self, id: int) -> AlignState:
        """ 
        获取指定 id 的状态 
        """
        for state in self._states:
            if state.id == id:
                return state
        return None
    
    def get_states(self) -> List[AlignState]:
        """ 
        获取所有状态 
        """
        return self._states
    
    def to_dict(self):
        """ 
        转换为字典 
        """
        return {
            "states": [state.to_dict() for state in self._states]
        }
    
    def __repr__(self):
        state_str = ""
        for state in self._states:
            state_str += str(state)
            if state != self._states[-1]:
                state_str += "\n"
        return f"HoState(\n{state_str})"

class HoLink(Node):
    """ Ho 机器人链接节点 """
    def __init__(self, name="HoLink", buffer_capacity: int=1024, url=None, warn=True) -> None:
        """ 
        初始化 Ho 机器人链接节点 

            :param name: 节点名称
            :param buffer_capacity: 存储状态数据的缓冲区的容量
            :param url: 数据发送的 url
            :param read_mode: 串口读取模式
            :param warn: 是否显示警告
        """
        super().__init__(name)
        self._data_length = 84
        self._receive_data = None
        self._url = url
        self._warn = warn
        
        if self._url:
            self._shutdown = multiprocessing.Event()
            self._pending_capacity = 256
            self._pending_requests = multiprocessing.Queue()
            self._http_process = multiprocessing.Process(target=self._http_request, daemon=True, name=self.name+"HttpProcess")
            self._http_process.start()

        self.buffer_capacity: int = buffer_capacity
        """ 存储状态数据的缓冲区的容量 """
        self.state_buffer: List[HoState] = []
        """ 存储状态数据的缓冲区 """

        self.sio: SerialIO = SerialIO(name="HoSerialIO", device_type=DeviceType.STM32F407, checksum_type=CheckSumType.SUM16, header=[0x0D, 0x0A], warn=warn, baudrate=1000000, timeout=1.0)
        """ 串口节点 HoLink 会主动挂载一个已经配置好的串口节点 """
        self.add_child(self.sio)

        self.receive: Signal = Signal(bytes)
        """ 信号，当接收到数据时触发(无论是否通过校验和) """
        self.robot_state_update: Signal = Signal(HoState)
        """ 信号，当接收到数据并成功通过校验和，将状态数据更新到信号参数中时触发 """

    def _ready(self) -> None:
        pass

    def _add_pending_request(self, ho_state: HoState):
        """ 
        向请求队列中添加请求 
        """
        self._pending_requests.put(ho_state)
        if self._pending_requests.qsize() > self._pending_capacity:
            if self._warn:
                warning(f"{self.name} 向 {self._url} 发送请求时，请求队列已满，将丢弃最早的请求，可能会导致数据丢失")
            self._pending_requests.get()

    def _send_request(self, ho_state_dict: dict) -> None:
        start_time = time.perf_counter()
        try:
            response = requests.post(self._url, json=ho_state_dict, timeout=0.1)

            end_time = time.perf_counter()
            latency = end_time - start_time
            # print(f"Request latency: {round(latency * 1000, 2)} ms")

        except requests.RequestException as e:
            if self._warn:
                warning(f"请求失败: {e}")
        except Exception as e:
            if self._warn:
                warning(f"发生未知错误: {e}")

    def _http_request(self):
        info(f"{self.name} 已开启向服务地址 {self._url} 发送数据的功能")
        while not self._shutdown.is_set():
            if not self._pending_requests.empty():
                ho_state = self._pending_requests.get()
                self._send_request(ho_state.to_dict())

    def update(self, id: int, mode: HoMode, i: float, v: float, p: float) -> None:
        """ 
        向机器人发送数据 
        """
        data = bytes([id]) + bytes([mode.value]) + self._encode(p, 100.0, 4) + \
            self._encode(v, 100.0, 4) + self._encode(i, 100.0, 2)
        # print(f"发送数据: {hex2str(data)}")
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

                ho_state = HoState(states)
                self.state_buffer.append(ho_state)

                if len(self.state_buffer) > self.buffer_capacity:
                    self.state_buffer.pop(0)

                self.robot_state_update.emit(ho_state)
                if self._url:
                    self._add_pending_request(ho_state)
            else:
                if self._warn:
                    warning(f"{self.name} 长度为 {len(self._receive_data)} 的数据 {hex2str(self._receive_data)} 校验和错误")
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
    
    # def _on_engine_exit(self):
    #     if self._url:
    #         self._shutdown.set()
    #         self._http_process.join()
            

class HoServer:
    def __init__(self, url: str, capacity=1024, ui: bool=True, ui_frequency: float=30.0) -> None:
        """
        初始化 HoServer 实例。

            :param url: 服务器的 URL。
            :param capacity: 数据缓冲区的最大容量。
            :param ui: 是否启用 UI 界面。
            :param ui_frequency: UI 更新频率（Hz）。
        """
        self._url = url
        parsed_url = urlparse(url)
        self._host = parsed_url.hostname
        self._port = parsed_url.port
        self._path = parsed_url.path

        self._ui = ui
        self._ui_frequency = ui_frequency
        self._capacity = capacity
        self._data_buffer = []
        """ 
        数据缓冲区 
        """

        self._data_queue = multiprocessing.Queue()
        self._shutdown = multiprocessing.Event()

        # 启动 FastAPI 应用进程
        self._app_process = multiprocessing.Process(target=self._run_app, args=(self._path, self._host, self._port), daemon=True)

    def _update_data(self):
        """
        从数据队列中读取数据并更新缓冲区。
        """
        while not self._shutdown.is_set():
            if not self._data_queue.empty():
                ho_state = self._data_queue.get()
                self._data_buffer.append(ho_state)
                if len(self._data_buffer) > self._capacity:
                    self._data_buffer.pop(0)

    def has_data(self):
        """
        检查缓冲区中是否有数据。

            :return: 如果缓冲区中有数据，则返回 True，否则返回 False。
        """
        return len(self._data_buffer) > 0

    def get_data(self) -> HoState:
        """
        获取缓冲区中最新的数据。

            :return: 缓冲区中最新的数据，如果缓冲区为空，则返回 None。
        """
        if not self.has_data():
            return None
        return self._data_buffer.pop(-1)
    
    def get_data_buffer(self) -> List[HoState]:
        """
        获取缓冲区。

        注意：若需要从数据缓冲区中读取数据，请尽快取出，否则缓冲区溢出后最开始的数据会丢失

            :return: 缓冲区。
        """
        return copy.deepcopy(self._data_buffer)
    
    def length(self) -> int:
        """
        获取缓冲区中的数据长度。

            :return: 缓冲区中的数据长度。
        """
        return len(self._data_buffer)

    def _init_ui(self) -> None:
        """
        初始化 UI。
        """
        self.root = tk.Tk()
        self.root.title("HoServer")
        self.root.geometry("800x600")

    def run(self) -> None:
        """
        启动服务器并运行 UI 更新线程（如果启用 UI）。
        """
        self._app_process.start()

        # 数据更新线程
        self._data_thread = threading.Thread(target=self._update_data, daemon=True)
        self._data_thread.start()

        if self._ui:
            self._init_ui()
            # UI 更新线程
            self._ui_thread = threading.Thread(target=self._update_ui, daemon=True)
            self._ui_thread.start()

            self.root.mainloop()

    def _run_app(self, path: str, host: str, port: int) -> None:
        """
        启动 FastAPI 服务器并监听请求。

            :param path: API 路径。
            :param host: 服务器主机。
            :param port: 服务器端口。
        """
        app = FastAPI()
        app.add_api_route(path, self._handle_data, methods=["POST"])

        uvicorn.run(app, host=host, port=port)

    async def _handle_data(self, request: Request) -> dict:
        """
        处理接收到的 POST 请求数据。

            :param request: FastAPI 请求对象。
            :return: 处理结果。
        """
        json_data = await request.json()
        states_data = json_data.get("states", [])

        states = []
        for state_data in states_data:
            state = AlignState(
                id=state_data["id"],
                i=state_data["i"],
                v=state_data["v"],
                p=state_data["p"],
                frame=state_data["frame"],
                timestamp=state_data["timestamp"]
            )
            states.append(state)
        
        ho_state = HoState(states=states)
        self._data_queue.put(ho_state)
        return {"message": "Data received"}

    def _init_ui(self) -> None:
        """
        初始化 UI 界面。
        """
        self.root = ttkb.Window(themename="superhero", title="HoServer")

        frame = ttk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        columns = ['Id', 'Frame', 'Timestamp', 'i', 'v', 'p']
        self.entries = {}

        # 创建表头
        for col, column_name in enumerate(columns):
            label = ttk.Label(frame, text=column_name, width=5)
            label.grid(row=0, column=col, padx=5, pady=5)

        # 创建数据输入框
        for row in range(8):
            id_label = ttk.Label(frame, text=f"{row + 1}", width=5)
            id_label.grid(row=row + 1, column=0, padx=5, pady=5)
            for col in range(5):
                entry = ttk.Entry(frame, width=15, state='normal')
                entry.grid(row=row + 1, column=col + 1, padx=5, pady=10)
                self.entries[(row, col)] = entry

    def _update_ui(self) -> None:
        """
        根据数据缓冲区更新 UI 界面。
        """
        def update() -> None:
            if len(self._data_buffer) == 0:
                return
            ho_state = self._data_buffer[-1]
            
            # 清空当前数据
            for row in range(8):
                for col in range(5):
                    self.entries[(row, col)].delete(0, tk.END)

            # 更新数据
            for row in range(8):
                align_state = ho_state.get_state(row + 1)
                self.entries[(row, 0)].insert(0, str(align_state.frame))
                self.entries[(row, 1)].insert(0, str(align_state.timestamp))
                self.entries[(row, 2)].insert(0, str(round(align_state.i, 2)))
                self.entries[(row, 3)].insert(0, str(round(align_state.v, 2)))
                self.entries[(row, 4)].insert(0, str(round(align_state.p, 2)))

        time_interval = 1.0 / self._ui_frequency
        while not self._shutdown.is_set():
            time.sleep(time_interval)

            self.root.after(0, update)


    def __del__(self) -> None:
        """
        清理资源，停止线程和进程。
        """
        self._shutdown.set()
        self._app_process.join()
        self._data_thread.join()
        if self._ui:
            self._ui_thread.join()



class ManualState(Enum):
    """ 手动状态枚举 """
    IDLE = 0
    """ 空闲 """
    ALIGN = 1
    """ 对齐 """
    SHOOT = 2
    """ 射击 """

class HoManual(Node):
    def __init__(self, link: HoLink, name="Manual") -> None:
        from robotengine import StateMachine
        super().__init__(name)
        self._link = link
        self.state_machine = StateMachine(ManualState.IDLE, name="StateMachine")


# if __name__ == "__main__":
#     ho_server = HoServer("http://127.0.0.1:7777/data", ui=False)
#     ho_server.run()
