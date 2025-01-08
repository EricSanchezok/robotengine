
def hex_to_str(data) -> str:
    return ' '.join(f'{byte:02X}' for byte in data)