import serial
import time

def compare_read_speeds(baudrate, read_size, iterations):
    ser = serial.Serial('COM15', baudrate, timeout=10)

    # 每次读取1个字节，重复读取read_size次
    def read_single_byte():
        total_bytes_read = 0
        for _ in range(read_size):
            data = ser.read(1)
            total_bytes_read += len(data)
        print(f"Single byte read {total_bytes_read} bytes")
        return total_bytes_read

    # 每次读取read_size个字节，重复读取1次
    def read_multiple_bytes():
        data = ser.read(read_size)
        print(f"Multiple bytes read {len(data)} bytes")
        return len(data)

    single_byte_times = []
    multiple_byte_times = []

    # 进行n次测试
    for _ in range(iterations):
        start_time = time.time()
        read_single_byte()
        elapsed_time = time.time() - start_time
        single_byte_times.append(elapsed_time)

        start_time = time.time()
        read_multiple_bytes()
        elapsed_time = time.time() - start_time
        multiple_byte_times.append(elapsed_time)

    # 计算平均时间
    avg_single_byte_time = sum(single_byte_times) / iterations
    avg_multiple_byte_time = sum(multiple_byte_times) / iterations

    print(f"Average time for reading 1 byte {read_size} times: {avg_single_byte_time} seconds")
    print(f"Average time for reading {read_size} bytes 1 time: {avg_multiple_byte_time} seconds")
    
    ser.close()


if __name__ == "__main__":
    baudrate = 1000000
    read_size = 65536
    iterations = 10
    compare_read_speeds(baudrate, read_size, iterations)