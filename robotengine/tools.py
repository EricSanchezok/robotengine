


def print_hex(data) -> None:
    hex_string = ' '.join(f'{byte:02X}' for byte in data)
    print(hex_string)