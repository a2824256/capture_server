import socket
import json
sk = socket.socket()
sk.connect(('127.0.0.1', 60000))
headcode = str(0xFFFFFFFF)
header = headcode
print(type(header))
body = '{"save":0,"patientid":"123456","caseid":"12345678"}'
content = header + body
# content = header
sk.send(content.encode())
sk.close()
