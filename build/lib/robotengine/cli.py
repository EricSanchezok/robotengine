import argparse
from .help_server import start_server

def main():
    parser = argparse.ArgumentParser(prog="robotengine")
    
    # 添加 --help 选项
    parser.add_argument("--help", action="help", help="Show help message and exit")

    # 添加自定义命令（如 --open-html）
    parser.add_argument("--open-html", action="store", type=str, default="docs\\robotengine.html", 
                        help="Open the specified HTML file (default is robotengine.html)")

    args = parser.parse_args()

    # 如果用户输入 --open-html，启动服务器并打开该 HTML 文件
    if args.open_html:
        start_server(html_file=args.open_html)

if __name__ == "__main__":
    main()
