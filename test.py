import multiprocessing
import threading
import time

def http_request():
    while True:
        print("HttpProcess is running")
        time.sleep(1)

# 创建进程（并不需要队列，除非有进程间通信）
http_process = multiprocessing.Process(target=http_request, daemon=False, name="HttpProcess")
http_process.start()

# 等待一段时间，以便查看输出
time.sleep(3)

# 打印当前运行的线程
print("Threading 模块正在运行的线程有： ")
for _thread in threading.enumerate():
    print(f"{_thread.ident} {_thread.name}")

# 等待子进程结束
http_process.join()
