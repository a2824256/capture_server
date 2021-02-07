import struct
length = 10
length = hex(length)
print(length[2:])
c = bytes.fromhex(str('0' + length[2:]))
print(c)