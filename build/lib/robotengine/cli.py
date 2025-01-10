import argparse
from robotengine.help_server import start_server

def main():
    parser = argparse.ArgumentParser(prog="robotengine")
    
    parser.add_argument(
        "--doc", 
        action="store", 
        type=str, 
        default="docs/robotengine.html",  
        nargs="?",
        help="Open the specified HTML file (default is robotengine.html)"
    )
    
    args = parser.parse_args()

    if args.doc:
        start_server(html_file=args.doc)

if __name__ == "__main__":
    main()
