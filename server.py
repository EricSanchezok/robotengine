from robotengine import HoServer, HoState

if __name__ == '__main__':
    ho_server = HoServer("http://127.0.0.1:7777/data", capacity=1024, ui=True, ui_frequency=30.0)
    ho_server.run()