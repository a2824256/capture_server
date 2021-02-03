import socket

if __name__ == '__main__':
    s = socket.socket()
    host = socket.gethostname()
    port = 60000
    s.bind((host, port))
    s.listen(5)
    print('server start')
    while 1:
        try:
            c, addr = s.accept()
            print(str(addr) + " connected")
            while 1:
                rec_data = c.recv(64)
                rec_data = str(rec_data, encoding='utf-8')
                print(rec_data)
        except:
            print('error')
            exit()