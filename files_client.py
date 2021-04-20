import socket
import os
import json
import struct

def send_file(sk, file_path, filename):
    # 定制我们的报头，这里的报头不是唯一的，你可以根据你的想法去更改
    head = {'filepath': file_path,
            'filename': filename,
            'filesize': None}
    file_path = os.path.join(STORE_PATH, file_path, head['filename'])
    # 计算文件的大小
    filesize = os.path.getsize(file_path)
    head['filesize'] = filesize
    json_head = json.dumps(head)  # 利用json将字典转成字符串
    bytes_head = json_head.encode('utf-8')  # 字符串转bytes
    # 计算head长度
    head_len = len(bytes_head)  # 报头的长度
    # 利用struct将int类型的数据打包成4个字节的byte，所以服务器端接受这个长度的时候可以固定缓冲区大小为4
    pack_len = struct.pack('i', head_len)
    # 先将报头长度发出去
    sk.send(pack_len)
    # 再发送bytes类型的报头
    sk.send(bytes_head)
    with open(file_path, 'rb') as f:
        while filesize:
            if filesize >= buffer:
                content = f.read(buffer)  # 每次读取buffer字节大小内容
                filesize -= buffer
                sk.send(content)  # 发送读取的内容
            else:
                content = f.read(filesize)
                sk.send(content)
                filesize = 0
                break

STORE_PATH = r'E:\PycharmProjects\capture_server2\down'
sk = socket.socket()
sk.connect(('127.0.0.1', 8888))  # 与服务器建立连接
file_path = r'test'
buffer = 1024
for _, dirs, _ in os.walk(STORE_PATH):
    for dir in dirs:
        if dir != '':
            for _, _, files in os.walk(os.path.join(STORE_PATH, dir)):
                for file in files:
                    send_file(sk, dir, file)
sk.close()