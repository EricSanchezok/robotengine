from robotengine import HoServer, HoState

if __name__ == '__main__':
    ho_server = HoServer("http://127.0.0.1:7777/data", capacity=1024, ui=False, ui_frequency=30.0)
    ho_server.run()

    while True:
        if ho_server.has_data():
            ho_state = ho_server.get_data()
            print(ho_server.length())