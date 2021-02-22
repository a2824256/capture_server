import socket
import pyrealsense2 as rs
import numpy as np
import cv2
import json
import png
import datetime
import os

headCode = b'\xff\xff\xff\xff'
MSG_Heart = '0000'
MSG_Save = '0002'
MSG_Heart_Ack_Msg_id = b'\x00\x01'
Crc_test = b'\x00'
Reserved_test = b'\x00'

status = 0


def mkdir(path):
    path = path.strip()
    path = path.rstrip("/")
    isExists = os.path.exists(path)

    if not isExists:
        os.makedirs(path)
        return True
    else:
        return False

def fitzero(str, bits):
    length = len(str)
    if length < bits:
        for i in range(bits - length):
            str = '0' + str
    return str

def get_aligned_images(pipeline, align):
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    aligned_depth_frame = aligned_frames.get_depth_frame()
    color_frame = aligned_frames.get_color_frame()
    depth_image = np.asanyarray(aligned_depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())
    return color_image, depth_image


def get_request_type(header, pipeline, align):
    # length: 96 bits
    global status
    body = header[12:]
    body_obj = json.loads(body)
    header = header[:12]
    # msg_id length: 16 bits
    msg_id = header.hex()[16:20]
    # MSG_Heart
    if msg_id == MSG_Save:
        try:
            status = 1
            patientid = body_obj['patientid']
            caseid = body_obj['caseid']
            now = datetime.datetime.now()
            otherStyleTime = now.strftime("%Y%m%d%H%M%S")
            file_path = './img/' + patientid + '_' + caseid + '_' + otherStyleTime + '/'
            res = mkdir(file_path)
            print(res)
            print(file_path)
            for i in range(20):
                color_image, depth_image = get_aligned_images(pipeline, align)
                writer16 = png.Writer(width=depth_image.shape[1], height=depth_image.shape[0],
                                      bitdepth=16, greyscale=True)
                cv2.imwrite(file_path + str(i) + '_rgb.jpg', color_image)
                with open(file_path + str(i) + '_depth.jpg', 'wb') as f:
                    zgray2list = depth_image.tolist()
                    writer16.write(f, zgray2list)
            status = 0
        except:
            print('error')
            status = 2
    # generate json
    json_obj = {}
    json_obj['status'] = status
    json_str = json.dumps(json_obj)
    # generate bytes
    body_len = len(bytes(json_str, encoding='utf-8')) + 12
    length_hex_str = hex(body_len).replace('0x', '')
    length_bytes = bytes.fromhex(fitzero(length_hex_str, 8))
    content = headCode + length_bytes + MSG_Heart_Ack_Msg_id + Crc_test + Reserved_test + bytes(json_str, encoding='utf-8')
    return content


if __name__ == '__main__':
    try:
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        profile = pipeline.start(config)
        align_to = rs.stream.color
        align = rs.align(align_to)
    except:
        status = 2

    # bak
    # color_image, depth_image = get_aligned_images(pipeline, align)

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
                if len(rec_data) > 0:
                    content = get_request_type(rec_data, pipeline, align)
                    c.send(content)
                c.close()
                break
            print(addr, " disconnected")
        except Exception as e:
            print(e)
            s.close()
            exit()
