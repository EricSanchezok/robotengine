import http.server
import socketserver
import webbrowser
import os

def start_server(html_file="docs\\robotengine.html", port=7777):
    """启动一个本地 HTTP 服务器并打开指定的 HTML 文件"""
    # 设置服务器工作目录为当前目录
    os.chdir(os.path.dirname(os.path.abspath(html_file)))

    # 启动 HTTP 服务器
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving at http://localhost:{port}")
        
        # 自动打开浏览器
        webbrowser.open(f'http://localhost:{port}/{html_file}')
        
        # 启动服务器并保持运行
        httpd.serve_forever()
