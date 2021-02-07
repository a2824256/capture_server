import socket
import pyrealsense2 as rs
import numpy as np
import cv2
import json
import png



def get_aligned_images(pipeline, align, profile):
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    aligned_depth_frame = aligned_frames.get_depth_frame()
    color_frame = aligned_frames.get_color_frame()
    depth_image = np.asanyarray(aligned_depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())
    return color_image, depth_image,


def get_request_type(header):
    # length: 96 bits
    header = header[2:]
    # msg_id length: 16 bits
    msg_id = header[64:64+16]
    # MSG_Heart
    if msg_id == '0000000000000000':
        print('Type:', 'MSG_Heart')
        print(bytes(b'0000000000000000', encoding='utf-8'))
    # MSG_Save
    elif msg_id == '0000000000000010':
        print('Type:', 'MSG_Save')
    return header


if __name__ == '__main__':

    # intelrealsense
    # pipeline = rs.pipeline()
    # config = rs.config()
    # config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
    # config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    # profile = pipeline.start(config)
    # align_to = rs.stream.color
    # align = rs.align(align_to)
    # depth_intrin = None

    # bak
    # color_image, depth_image = get_aligned_images(pipeline, align, profile)

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
                print(len(rec_data))
                print(rec_data)
                exit()
                if len(rec_data) > 0:
                    str = rec_data.decode()
                    header = str.split('{')[0]
                    body = '{' + str.split('{')[1].split('}')[0] + '}'
                    header = bin(int(header))
                    get_request_type(header)
                    # print(header[65:81])
                    # print('length:', len(header[2:]))
                    print(body)
                c.close()
                break
            print(addr, " disconnected")
        except Exception as e:
            print(e)
            s.close()
            exit()