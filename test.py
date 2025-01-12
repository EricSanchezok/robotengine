import tkinter as tk
from ttkbootstrap import ttk
import ttkbootstrap as ttkb
from fastapi import FastAPI, Request
import uvicorn
from robotengine import AlignState, HoState
import multiprocessing
import threading
from urllib.parse import urlparse
import time


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
        self.data_buffer = []

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
                self.data_buffer.append(ho_state)
                if len(self.data_buffer) > self._capacity:
                    self.data_buffer.pop(0)

    def run(self):
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

    def _run_app(self, path: str, host: str, port: int):
        """
        启动 FastAPI 服务器并监听请求。

        :param path: API 路径。
        :param host: 服务器主机。
        :param port: 服务器端口。
        """
        app = FastAPI()
        app.add_api_route(path, self._handle_data, methods=["POST"])

        uvicorn.run(app, host=host, port=port)

    async def _handle_data(self, request: Request):
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

    def _update_ui(self):
        """
        根据数据缓冲区更新 UI 界面。
        """
        def update() -> None:
            if len(self.data_buffer) == 0:
                return
            ho_state = self.data_buffer[-1]
            
            # 清空当前数据
            for row in range(8):
                for col in range(5):
                    self.entries[(row, col)].delete(0, tk.END)

            # 更新数据
            for row in range(8):
                align_state = ho_state.get_state(row + 1)
                self.entries[(row, 0)].insert(0, str(align_state.frame))
                self.entries[(row, 1)].insert(0, str(round(align_state.timestamp, 2)))
                self.entries[(row, 2)].insert(0, str(round(align_state.i, 2)))
                self.entries[(row, 3)].insert(0, str(round(align_state.v, 2)))
                self.entries[(row, 4)].insert(0, str(round(align_state.p, 2)))

        time_interval = 1.0 / self._ui_frequency
        while not self._shutdown.is_set():
            time.sleep(time_interval)

            self.root.after(0, update)


    def __del__(self):
        """
        清理资源，停止线程和进程。
        """
        self._shutdown.set()
        self._app_process.join()
        self._data_thread.join()
        if self._ui:
            self._ui_thread.join()


if __name__ == "__main__":
    ho_server = HoServer("http://127.0.0.1:7777/data", ui=False)
    ho_server.run()
