import aiohttp
import asyncio
import time
import json
from robotengine import HoState

# 发送请求并返回延迟时间
async def send_request(url, ho_state: HoState):
    start_time = time.perf_counter()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=ho_state.to_dict()) as response:
                end_time = time.perf_counter()
                latency = end_time - start_time

                response_data = await response.json()

                print(f"Response status: {response.status}")
                print(f"Response data: {response_data}")
                return latency  # 返回本次请求的延迟时间

        except Exception as e:
            print(f"Request failed: {e}")
            return None  # 如果请求失败，返回 None

# 主函数，执行多次请求并计算平均延迟
async def main():
    url = "http://127.0.0.1:7777/data"
    num_requests = 100  # 测试请求的次数
    latencies = []

    for _ in range(num_requests):
        latency = await send_request(url, HoState([], random_state=True))
        if latency is not None:
            latencies.append(latency)

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average latency over {num_requests} requests: {avg_latency:.4f} seconds")
    else:
        print("No successful requests were made.")

if __name__ == "__main__":
    asyncio.run(main())
