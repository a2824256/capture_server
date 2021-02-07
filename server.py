import socket
import pyrealsense2 as rs
import numpy as np
import cv2
import json
import png



if __name__ == '__main__':
    s = socket.socket()
    host = '127.0.0.1'
    print('host:', host)
    port = 60000
    s.bind((host, port))
    s.listen(5)
    print('start')
    while True:
        try:
            c, addr = s.accept()
            print(addr, " connected")
            while True:
                rec_data = c.recv(1024)
                rec_data = rec_data
                if len(rec_data) > 0:
                    str = rec_data.decode()
                    header = str.split('{')[0]
                    body = '{' + str.split('{')[1].split('}')[0] + '}'
                    header = bin(int(header))
                    print(header[0:2])
                    print(body)
                c.close()
                break
            print(addr, " disconnected")
        except:
            print('error')
            s.close()
            exit()