
def hex_to_str(data) -> str:
    return ' '.join(f'{byte:02X}' for byte in data)


def warning(msg) -> None:
    msg = f"[WARNING] {msg}"
    print(f"\033[33m{msg}\033[0m")

def error(msg) -> None:
    msg = f"[ERROR] {msg}"
    print(f"\033[31m{msg}\033[0m")
    exit(1)