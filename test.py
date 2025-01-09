from robotengine import tools


data = [0x0A for _ in range(32)]

check_sum = sum(data) & 0xFFFF
print(hex(check_sum))

print(tools.hex_to_str(check_sum.to_bytes(2, byteorder='big')))

print(tools.hex_to_str(check_sum.to_bytes(2, byteorder='little')))
