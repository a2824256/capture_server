import socket
import json
sk = socket.socket()
sk.connect(('127.0.0.1', 60000))
# 0xFFFF FFFF 0000 0064 0000 1111
header = b'\xff\xff\xff\xff' + b'\x00\x00' + b'\x00\x64' + b'\x00\x02' + b'\x10\x10'
# print(type(header))
body = bytes('{"save":0,"patientid":"123456","caseid":"12345678"}', encoding='utf-8')
content = header + body
# content = header
sk.send(content)
sk.close()
