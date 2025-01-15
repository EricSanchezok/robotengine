"""

ho_robot 是 robotengine 控制 ho 机器人的节点。

ho_link 与 机器人之间的通讯是自动的，在连接好设备并确定串口是正常开启后，会自动与机器人进行通讯并更新。

如果配置了 url ho_link 节点会自动发送机器人的状态 HoState 到 url 指定的地址。

ho_link 会不断被动地接收机器人的状态并更新，但是不会主动向机器人发送数据。

使用 ho_link.update() 函数可以向机器人发送数据。

挂载 ho_link 节点后，_process()的处理速度会显著受到影响，请酌情调整 engine 的运行频率。
"""

from robotengine.node import Node
from robotengine.serial_io import SerialIO, DeviceType, CheckSumType
from robotengine.tools import hex2str, warning, error, info, near, vector_angle, vector_length, compute_vector_projection, find_closest_vectors
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
import math
import json
import os

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
        return copy.deepcopy(self._states)
    
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
    def __init__(self, name="HoLink", buffer_capacity: int=1024, urls: List[str]=[], warn=True) -> None:
        """ 
        初始化 Ho 机器人链接节点 

            :param name: 节点名称
            :param buffer_capacity: 存储状态数据的缓冲区的容量
            :param urls: 服务地址列表
            :param read_mode: 串口读取模式
            :param warn: 是否显示警告
        """
        super().__init__(name)
        self._data_length = 84
        self._receive_data = None
        self._urls = urls
        self._warn = warn
        
        if self._urls:
            self._shutdown = multiprocessing.Event()
            self._pending_capacity = 256
            self._pending_requests = multiprocessing.Queue()
            self._http_process = multiprocessing.Process(target=self._http_request, daemon=True, name=self.name+"HttpProcess")
            self._http_process.start()

        self._buffer_capacity: int = buffer_capacity
        """ 存储状态数据的缓冲区的容量 """
        self._state_buffer: List[HoState] = []
        """ 存储状态数据的缓冲区 """

        self.sio: SerialIO = SerialIO(name="HoSerialIO", device_type=DeviceType.STM32F407, checksum_type=CheckSumType.SUM16, header=[0x0D, 0x0A], warn=warn, baudrate=1000000, timeout=1.0)
        """ 串口节点 HoLink 会主动挂载一个已经配置好的串口节点 """
        self.add_child(self.sio)

        self.receive: Signal = Signal(bytes)
        """ 信号，当接收到数据时触发(无论是否通过校验和) """
        self.ho_state_update: Signal = Signal(HoState)
        """ 信号，当接收到数据并成功通过校验和，将状态数据更新到信号参数中时触发 """

    def _ready(self) -> None:
        pass

    def get_ho_state(self) -> HoState:
        """
        获取机器人当前最新的状态数据
        """
        if len(self._state_buffer) == 0:
            return None
        return self._state_buffer[-1]
    
    def get_ho_state_buffer(self) -> List[HoState]:
        """
        获取机器人当前的状态数据缓冲区
        """
        return copy.deepcopy(self._state_buffer)

    def _add_pending_request(self, ho_state: HoState):
        """ 
        向请求队列中添加请求 
        """
        self._pending_requests.put(ho_state)
        if self._pending_requests.qsize() > self._pending_capacity:
            if self._warn:
                warning(f"{self.name} 向 {self._urls} 发送请求时，请求队列已满，将丢弃最早的请求，可能会导致数据丢失")
            self._pending_requests.get()

    def _send_request(self, ho_state_dict: dict) -> None:
        """
        向服务地址发送请求
        """
        try:
            for _url in self._urls:
                response = requests.post(_url, json=ho_state_dict, timeout=0.1)

        except requests.RequestException as e:
            if self._warn:
                warning(f"请求失败: {e}")
        except Exception as e:
            if self._warn:
                warning(f"发生未知错误: {e}")

    def _http_request(self):
        info(f"{self.name} 已开启向服务地址 {self._urls} 发送数据的功能")
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
                self._state_buffer.append(ho_state)

                if len(self._state_buffer) > self._buffer_capacity:
                    self._state_buffer.pop(0)

                self.ho_state_update.emit(ho_state)
                if self._urls:
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
    #     if self._urls:
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
        self._urls = url
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

    def has_data(self) -> bool:
        """
        检查缓冲区中是否有数据。

            :return: 如果缓冲区中有数据，则返回 True，否则返回 False。
        """
        return len(self._data_buffer) > 0

    def get_data(self) -> HoState:
        """
        获取缓冲区中最新的数据。

            :return: 缓冲区中最老的数据，如果缓冲区为空，则返回 None。
        """
        if not self.has_data():
            return None
        return self._data_buffer.pop(0)
    
    def get_data_buffer(self) -> List[HoState]:
        """
        获取缓冲区。

        注意：若需要从数据缓冲区中读取数据，请尽快取出，否则缓冲区溢出后最开始的数据会丢失

            :return: 缓冲区。
        """
        return copy.deepcopy(self._data_buffer)
    
    def flush(self) -> None:
        """
        清空缓冲区。
        """
        self._data_buffer.clear()
    
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
    """ 空闲状态，所有电机停止运动 """
    RUNNING = 1
    """ 运行状态 """
    RETURNING = 2
    """ 返回状态 """
    ZEROING = 3
    """ 设置零点状态 """

class HoManual(Node):
    """ Ho 机器人的手动控制节点 """
    from robotengine import InputEvent
    def __init__(self, link: HoLink, name="Manual", rotation_velocity: float = 360.0, running_scale: float=100.0, zeroing_scale: float=100.0, axis_threshold: float=0.1) -> None:
        """
        初始化 HoManual 实例。

            :param link: HoLink 实例。
            :param name: 节点名称。
            :param rotation_velocity: 旋转速度（度/秒）。
            :param running_scale: 运行状态的缩放因子。
            :param zeroing_scale: 设置零点状态的缩放因子。
            :param axis_threshold: 轴的阈值。
        """
        from robotengine import StateMachine
        super().__init__(name)
        self._debug = False
        self._valid = True

        self._link = link
        self._link.ho_state_update.connect(self._on_ho_state_update)
        
        self.state_machine = StateMachine(ManualState.IDLE, name="HoManualStateMachine")
        self.add_child(self.state_machine)
        
        self._zero_angles = {
            4: 0.0,
            5: 0.0,
            6: 0.0,
            7: 0.0,
        }
        self._zero_index = 4

        self._is_tension = False
        self._is_rotation = False
        self._rotation_velocity = rotation_velocity
        self._base_angles = [math.pi / 4, math.pi / 4 * 3, math.pi / 4 * 5, math.pi / 4 * 7]

        self._running_scale = running_scale
        self._zeroing_scale = zeroing_scale
        self._axis_threshold = axis_threshold

        self._before_returning = None

        self.exit()

    def _init(self):
        _load_zero_angles = self._load_from_json("zero_angles.json")
        if _load_zero_angles:
            info("成功加载 zero_angles.json")
            for i in range(4, 8):
                self._zero_angles[i] = _load_zero_angles[str(i)]
                info(f"{i}: {self._zero_angles[i]}")

    def _input(self, event: InputEvent) -> None:
        if not self._valid:
            return
        
        state = self.state_machine.current_state

        if event.is_action_pressed("X"):
            self.tension(not self._is_tension)

        elif event.is_action_pressed("Y"):
            self.rotation(not self._is_rotation, self._rotation_velocity)

        if state == ManualState.ZEROING:
            if event.is_action_pressed("LEFT_SHOULDER"):
                self._change_index(-1)

            elif event.is_action_pressed("RIGHT_SHOULDER"):
                self._change_index(1)

            elif event.is_action_pressed("A"):
                if self._debug:
                    return
                ho_state = self._link.get_ho_state()
                if not ho_state:
                    return
                for i in range(4, 8):
                    state = ho_state.get_state(i)
                    self._zero_angles[i] = state.p
                self._save_to_json("zero_angles.json", self._zero_angles)

    def _change_index(self, dir: int) -> None:
        self.lock(self._zero_index)
        self._zero_index += dir
        if self._zero_index > 7:
            self._zero_index = 4
        elif self._zero_index < 4:
            self._zero_index = 7
        info(f"     当前电机: {self._zero_index}")

    def _on_ho_state_update(self, ho_state: HoState):
        if not self._valid:
            return
        
        state = self.state_machine.current_state

        if state == ManualState.IDLE:
            pass

        elif state == ManualState.RUNNING:
            x_value = self._threshold(self.input.get_action_strength("RIGHT_X"))
            y_value = self._threshold(self.input.get_action_strength("LEFT_Y"))
            self.turn(x_value, y_value, ho_state)

            l_value = self._threshold(self.input.get_action_strength("TRIGGER_LEFT"))
            r_value = self._threshold(self.input.get_action_strength("TRIGGER_RIGHT"))
            self.move(l_value, r_value, ho_state)

        elif state == ManualState.RETURNING:
            for i in range(4, 8):
                self._link.update(i, HoMode.P, 2.0, 100.0, self._zero_angles[i])

        elif state == ManualState.ZEROING:
            direction = self.input.get_action_strength("LEFT_Y")
            direction = self._threshold(direction)
            velocity = direction * self._zeroing_scale
            if not self._debug:
                self._link.update(self._zero_index, HoMode.V, 2.0, velocity, 0.0)

    def tick(self, state: ManualState, delta: float) -> None:
        if state == ManualState.IDLE:
            pass

        elif state == ManualState.RUNNING:
            pass

        elif state == ManualState.RETURNING:
            pass

        elif state == ManualState.ZEROING:
            pass

    def _threshold(self, value: float) -> float:
        if abs(value) < self._axis_threshold:
            return 0.0
        return value

    def get_next_state(self, state: ManualState) -> ManualState:
        if state == ManualState.IDLE:
            if self.input.is_action_pressed("START"):
                self.input.flush_action("START")
                return ManualState.RUNNING
            
            if self.input.is_action_pressed("B"):
                self.input.flush_action("B")
                return ManualState.RETURNING
            
            elif self.input.is_action_pressed("RIGHT_STICK"):
                self.input.flush_action("RIGHT_STICK")
                return ManualState.ZEROING

        elif state == ManualState.RUNNING:
            if self.input.is_action_pressed("START"):
                self.input.flush_action("START")
                return ManualState.IDLE
            
            if self.input.is_action_pressed("B"):
                self.input.flush_action("B")
                return ManualState.RETURNING

        elif state == ManualState.RETURNING:
            if self.input.is_action_pressed("B"):
                self.input.flush_action("B")
                return self._before_returning

        elif state == ManualState.ZEROING:
            if self.input.is_action_pressed("RIGHT_STICK"):
                self.input.flush_action("RIGHT_STICK")
                return ManualState.IDLE

        return self.state_machine.KEEP_CURRENT
    
    def transition_state(self, from_state: ManualState, to_state: ManualState) -> None:
        print("")
        info(f"{from_state if from_state is not None else 'START'} -> {to_state}")
        info(f"TENSION: {self._is_tension}, ROTATION: {self._is_rotation}")

        if from_state == ManualState.IDLE:
            pass

        elif from_state == ManualState.RUNNING:
            pass

        elif from_state == ManualState.RETURNING:
            pass

        elif from_state == ManualState.ZEROING:
            pass

        info("      Y: 开关旋转")
        info("      X: 开关张紧")
        if to_state == ManualState.IDLE:
            for i in range(1, 9):
                if i == 2 or i == 3:
                    continue
                self.stop(i)
            info("      START: 进入 RUNNING 状态")
            info("      B: 进入 RETURNING 状态")
            info("      RIGHT_STICK: 进入 ZEROING 状态")

        elif to_state == ManualState.RUNNING:
            for i in range(1, 9):
                if i == 2 or i == 3:
                    continue
                self.lock(i)
            info("      START: 返回 IDLE 状态")
            info("      B: 进入 RETURNING 状态")
    
        elif to_state == ManualState.RETURNING:
            self.lock(1)
            self._before_returning = from_state
            info("      B: 返回之前的状态")

        elif to_state == ManualState.ZEROING:
            for i in range(1, 9):
                if i == 2 or i == 3:
                    continue
                self.lock(i)
            info("      RIGHT_STICK: 返回 IDLE 状态")
            info("      LEFT_SHOULDER: 切换到上一个电机")
            info("      RIGHT_SHOULDER: 切换到下一个电机")
            info("      A: 保存当前位置为零点")
            info(f"      当前电机: {self._zero_index}")
    
    def lock(self, id: int) -> None:
        """
        锁定指定的电机。

            :param id: 电机编号
        """
        if self._debug:
            info(f"{self.name} 锁定电机 {id}")
            return
        self._link.update(id, HoMode.V, 2.0, 0.0, 0.0)

    def lock_all(self) -> None:
        """
        锁定所有的电机。
        """
        for i in range(1, 9):
            self.lock(i)

    def stop(self, id: int) -> None:
        """
        停止指定的电机。

            :param id: 电机编号
        """
        if self._debug:
            info(f"{self.name} 停止电机 {id}")
            return
        self._link.update(id, HoMode.S, 0.0, 0.0, 0.0)

    def stop_all(self) -> None:
        """
        停止所有的电机。
        """
        for i in range(1, 9):
            self.stop(i)

    def tension(self, on: bool, i: float=0.8) -> None:
        """
        驱动牵引电机，张紧导管

            :param on: 是否开启牵引
            :param i: 牵引电流（A）
        """
        self._is_tension = on
        if on:
            self._link.update(2, HoMode.V, i, -360.0, 0.0)
            self._link.update(3, HoMode.V, i, 360.0, 0.0)
        else:
            self.stop(2)
            self.stop(3)

    def rotation(self, on: bool, velocity: float = 360.0) -> None:
        """
        驱动旋转电机，旋转换能器

            :param on: 是否开启旋转
            :param velocity: 旋转速度（度/秒）
        """
        self._is_rotation = on
        if on:
            self._link.update(8, HoMode.V, 2.0, velocity, 0.0)
        else:
            self.stop(8)

    def turn(self, x_value: float, y_value: float, ho_state: HoState) -> None:
        """
        驱动转向电机，转向导管

            :param x_value: 横向控制值
            :param y_value: 纵向控制值
            :param ho_state: Ho 机器人状态
        """
        if x_value == 0 and y_value == 0:
            for i in range(4, 8):
                self._link.update(i, HoMode.V, 2.0, 0.0, 0.0)
        else:
            projection = compute_vector_projection(x_value, y_value, self._base_angles)
            control_values = [v * self._running_scale for v in projection]

            for i in range(4, 8):
                if control_values[i-4] > 0:
                    a_id = i
                    b_id = (i + 2) % 4 + 4
                    a_state = ho_state.get_state(a_id)
                    b_state = ho_state.get_state(b_id)
                    a_near = near(a_state.p, self._zero_angles[a_id])
                    b_near = near(b_state.p, self._zero_angles[b_id])

                    if a_near and not b_near:
                        self._link.update(b_id, HoMode.P, 2.0, control_values[i-4], self._zero_angles[b_id])
                    elif (not a_near and b_near) or (a_near and b_near):
                        self._link.update(a_id, HoMode.V, 2.0, control_values[i-4], 0.0)
                    elif not a_near and not b_near:
                        self._link.update(a_id, HoMode.V, 2.0, control_values[i-4], 0.0)
                        self._link.update(b_id, HoMode.P, 2.0, control_values[i-4], self._zero_angles[b_id])

    def move(self, l_value: float, r_value: float, ho_state: HoState) -> None:
        """
        驱动移动电机，移动导管

            :param l_value: 左侧移动控制值
            :param r_value: 右侧移动控制值
            :param ho_state: Ho 机器人状态
        """
        if l_value != 0 and r_value != 0:
            self._link.update(1, HoMode.V, 2.0, 0.0, 0.0)

        elif l_value != 0 and r_value== 0:
            self._link.update(1, HoMode.V, 2.0, -l_value * self._running_scale, 0.0)

        elif r_value != 0 and l_value== 0:
            self._link.update(1, HoMode.V, 2.0, r_value * self._running_scale, 0.0)

        else:
            self._link.update(1, HoMode.V, 2.0, 0.0, 0.0)

    def is_running(self) -> bool:
        """
        判断当前节点是否处于运行状态。

            :return: 如果当前节点处于运行状态，则返回 True，否则返回 False。
        """
        return self._valid

    def enter(self) -> None:
        """
        进入节点。
        """
        self.state_machine.freeze = False
        self.state_machine.first_tick = True
        self.state_machine.current_state = ManualState.IDLE
        self._is_rotation = False
        self._is_tension = False
        self._valid = True

    def exit(self) -> None:
        """
        退出节点。
        """
        self.state_machine.freeze = True
        self.state_machine.first_tick = True
        self.state_machine.current_state = ManualState.IDLE
        self._valid = False
        self._is_rotation = False
        self._is_tension = False
        self.stop_all()

    def _save_to_json(self, file_name, data):
        with open(file_name, 'w') as f:
            json.dump(data, f)
        info(f"     {self.name} 保存 {file_name} 成功")

    def _load_from_json(self, file_name):
        if not os.path.exists(file_name):
            warning(f"{file_name} 不存在，无法读取 zero_angles 将使用 0.0 作为初始值")
            return None
        with open(file_name, 'r') as f:
            return json.load(f)


