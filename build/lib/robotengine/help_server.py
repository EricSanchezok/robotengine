import http.server
import socketserver
import webbrowser
import os
import socket

def find_free_port():
    """找到一个空闲的端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))  # 绑定到一个随机空闲端口
        return s.getsockname()[1]  # 返回分配的端口

def start_server(html_file=""):
    abspath = os.path.abspath(html_file)
    file_dir = os.path.dirname(abspath)
    print("绝对路径：", abspath)
    print(f"切换到目录：{file_dir}")
    os.chdir(file_dir)

    if not os.path.exists(abspath):
        print(f"File not found: {abspath}")
        return

    port = find_free_port()

    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving at http://localhost:{port}")

        relative_file_url = os.path.relpath(abspath, file_dir).replace("\\", "/")

        webbrowser.open(f'http://localhost:{port}/{relative_file_url}')

        httpd.serve_forever()

