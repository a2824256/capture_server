import socket
import struct
import json
import os
socket.setdefaulttimeout(10)
STORE_PATH = './test'
sk = socket.socket()
sk.bind(('127.0.0.1', 8888))  # 绑定ip地址和端口
sk.listen()  # 开启监听

buffer = 1024  # 缓冲区大小，这里好像因为windows的系统的原因，这个接收的缓冲区不能太大
while True:
    try:
        conn, addr = sk.accept()
        while True:
            try:
                # 先接收报头的长度
                head_len = conn.recv(4)
                head_len = struct.unpack('i', head_len)[0]  # 将报头长度解包出来
                # 再接收报头
                json_head = conn.recv(head_len).decode('utf-8')  # 拿到的是bytes类型的数据，要进行转码
                head = json.loads(json_head)  # 拿到原本的报头
                print(head)
                file_size = head['filesize']
                save_path = os.path.join(STORE_PATH, head['filepath'])
                if not os.path.exists(save_path):
                    os.makedirs(save_path)
                save_file_path = os.path.join(save_path, head['filename'])
                # print(save_file_path)
                with open(save_file_path, 'ab') as f:
                    while file_size:
                        if file_size >= buffer:  # 判断剩余文件的大小是否超过buffer
                            content = conn.recv(buffer)
                            f.write(content)
                            file_size -= buffer
                        else:
                            content = conn.recv(file_size)
                            f.write(content)
                            file_size = 0
                            break
                # conn.close()
            except:
                # print('close')
                conn.close()
                break
    except:
        # print('continue')
        continue
sk.close()