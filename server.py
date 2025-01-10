import tkinter as tk
from ttkbootstrap import ttk
import ttkbootstrap as ttkb
from fastapi import FastAPI, Request
import uvicorn
import asyncio
import time
import queue
from robotengine import AlignState, HoRobotState

app = FastAPI()

@app.post("/data")
async def handle_data(request: Request):
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
    
    ho_robot_state = HoRobotState(states=states)
    
    root.after(0, update_motor_data, ho_robot_state)
    
    return {"message": "Data received"}

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=7777)

def update_motor_data(robot_state: HoRobotState):
    for row in range(8):
        entries[(row, 0)].delete(0, tk.END)
        entries[(row, 1)].delete(0, tk.END)
        entries[(row, 2)].delete(0, tk.END)
        entries[(row, 3)].delete(0, tk.END)
        entries[(row, 4)].delete(0, tk.END)

    for row in range(8):
        align_state = robot_state.get_state(row + 1)
        entries[(row, 0)].insert(0, str(align_state.frame))
        entries[(row, 1)].insert(0, str(round(align_state.timestamp, 2)))
        entries[(row, 2)].insert(0, str(round(align_state.i, 2)))
        entries[(row, 3)].insert(0, str(round(align_state.v, 2)))
        entries[(row, 4)].insert(0, str(round(align_state.p, 2)))

if __name__ == "__main__":
    root = ttkb.Window(themename="superhero", title="Motor Data")

    frame = ttk.Frame(root)
    frame.pack(padx=10, pady=10)

    columns = ['Id', 'Frame', 'Timestamp', 'i', 'v', 'p']

    entries = {}

    for col, column_name in enumerate(columns):
        label = ttk.Label(frame, text=column_name, width=5)
        label.grid(row=0, column=col, padx=5, pady=5)

    for row in range(8):
        id_label = ttk.Label(frame, text=f"{row+1}", width=5)
        id_label.grid(row=row+1, column=0, padx=5, pady=5)
        for col in range(5):
            entry = ttk.Entry(frame, width=15, state='normal')
            entry.grid(row=row+1, column=col+1, padx=5, pady=10)
            entries[(row, col)] = entry

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_server)

    root.mainloop()
