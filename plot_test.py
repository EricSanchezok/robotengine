from fastapi import FastAPI, Request
import uvicorn
import asyncio
import time
import queue
from robotengine import AlignState, HoRobotState
import matplotlib.pyplot as plt

app = FastAPI()

state_queue = queue.Queue()

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
    
    state_queue.put(ho_robot_state)
    
    return {"message": "Data received"}

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=7777)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_server)

    i_data = []
    v_data = []
    p_data = []
    timestamps = []
    frames = []

    fig, axes = plt.subplots(2, 2, figsize=(8, 4))
    ax1, ax2, ax3, ax4 = axes.flatten()

    lines_i = [ax1.plot([], [], label=f"id {i+1}")[0] for i in range(8)]
    lines_v = [ax2.plot([], [], label=f"id {i+1}")[0] for i in range(8)]
    lines_p = [ax3.plot([], [], label=f"id {i+1}")[0] for i in range(8)]

    ax1.set_title("I vs Frame")
    ax2.set_title("V vs Frame")
    ax3.set_title("P vs Frame")
    ax4.set_title("Empty Plot")

    for ax in [ax1, ax2, ax3]:
        ax.set_xlabel("Frame")
        ax.set_ylabel("v")

    update_frequency = 5
    length = 1000

    pending_states = []


    while True:
        if not state_queue.empty():
            pending_states.append(state_queue.get())

        if len(pending_states) >= update_frequency:
            for state in pending_states:
                state = state_queue.get()

                i_data += [state.get_state(i).i for i in range(1, 9)]
                v_data += [state.get_state(i).v for i in range(1, 9)]
                p_data += [state.get_state(i).p for i in range(1, 9)]
                timestamps += [state.get_state(i).timestamp for i in range(1, 9)]
                frames += [state.get_state(i).frame for i in range(1, 9)]

                i_data = i_data[-length:]
                v_data = v_data[-length:]
                p_data = p_data[-length:]
                timestamps = timestamps[-length:]
                frames = frames[-length:]

            for i in range(8):
                lines_i[i].set_data(frames, i_data[i])
                lines_v[i].set_data(frames, v_data[i])
                lines_p[i].set_data(frames, p_data[i])

            ax1.set_ylim(min(i_data), max(i_data))
            ax2.set_ylim(min(v_data), max(v_data))
            ax3.set_ylim(min(p_data), max(p_data))
            
            for ax in [ax1, ax2, ax3]:
                ax.set_xlim(min(frames), max(frames))
                ax.legend()

            plt.pause(0.01)
            pending_states = []

