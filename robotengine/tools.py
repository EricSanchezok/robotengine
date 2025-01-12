
def hex2str(data) -> str:
    return ' '.join(f'{byte:02X}' for byte in data)

def warning(msg) -> None:
    msg = f"[WARNING] {msg}"
    print(f"\033[33m{msg}\033[0m")

def error(msg) -> None:
    msg = f"[ERROR] {msg}"
    print(f"\033[31m{msg}\033[0m")
    exit(1)

def info(msg) -> None:
    msg = f"[INFO] {msg}"
    print(f"\033[32m{msg}\033[0m")

def get_variable_name(obj):
    for name, val in globals().items():
        if val is obj:
            return name
    return None
