import datetime
import time
import numpy as np
import pyrealsense2 as rs
import cv2
from threading import Lock,Thread
import socket
socket.setdefaulttimeout(10)

global_nd_rgb = None
global_nd_depth = None
STOP_SIG = False

# 获取对齐的rgb与深度图
def get_aligned_images(pipeline, align):
    # 等待获取单帧数据
    frames = pipeline.wait_for_frames()
    # 获取对齐后的单帧数据
    aligned_frames = align.process(frames)
    # 获取对齐后的深度帧
    aligned_depth_frame = aligned_frames.get_depth_frame()
    # 获取对齐后的彩色帧
    color_frame = aligned_frames.get_color_frame()
    # 获取深度图和彩色图，类型为ndarray
    depth_image = np.asanyarray(aligned_depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())
    return color_image, depth_image

def camera_threading():
    global global_nd_rgb, global_nd_depth
    print('thread start')
    pipeline = rs.pipeline()
    # 获取配置设置
    config = rs.config()
    # 设置深度图
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 60)
    # 设置rgb图
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 60)
    # 开启管道
    profile = pipeline.start(config)
    # 获取彩色流对象
    align_to = rs.stream.color
    # 获取对齐的流对象
    align = rs.align(align_to)
    while 1:
        if STOP_SIG:
            print('thread exit')
            exit()
        global_nd_rgb, global_nd_depth = get_aligned_images(pipeline, align)


# 主函数
if __name__ == '__main__':
    try:
        thread1 = Thread(target=camera_threading)
        thread1.start()
        while 1:
            if type(global_nd_rgb) == np.ndarray:
                cv2.imshow('test', global_nd_rgb)
                cv2.waitKey(10)
    except:
        STOP_SIG = True

