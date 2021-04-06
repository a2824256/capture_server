import socket
# intelrealsense驱动库
import pyrealsense2 as rs
import numpy as np
import cv2
import json
import png
import datetime
import os
import struct
from socket import gethostbyname, gethostname
from threading import Lock, Thread
socket.setdefaulttimeout(10)


# 请求头数据
headCode = b'\xff\xff\xff\xff'
MSG_Heart = '0000'
MSG_Save = '0200'
MSG_Heart_Ack_Msg_id = b'\x01\x00'
MSG_Save_Ack_Msg_id = b'\x03\x00'
Crc_test = b'\x00'
Reserved_test = b'\x00'
capture_number = 5

status = 0

# 视频采集
global_nd_rgb = None
global_nd_depth = None
STOP_SIG = False
FIRST_TIPS = True

# 创建文件夹函数
# path：要创建的文件夹路径
def mkdir(path):
    path = path.strip()
    path = path.rstrip("/")
    isExists = os.path.exists(path)

    if not isExists:
        os.makedirs(path)
        return True
    else:
        return False

# 字符串左侧填充0函数
# str：字符串
# bits：字符串最终要达到的位数
def fitzero(str, bits):
    length = len(str)
    if length < bits:
        for i in range(bits - length):
            str = '0' + str
    return str

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

# 获取返回结果
# data：数据包
# pipeline：intelrealsense管道
# align：对齐数据流对象
def get_return(data):
    # length: 96 bits
    # 使用全局的status变量
    global status, global_nd_rgb, global_nd_depth
    # 获取请求头
    header = data[:12]
    # 获取msg_id
    msg_id = header.hex()[16:20]
    MSG_id_bytes = MSG_Heart_Ack_Msg_id
    # 如果是采集操作
    if msg_id == MSG_Save:
        MSG_id_bytes = MSG_Save_Ack_Msg_id
        try:
            # 获取content
            body = data[12:]
            if len(body) > 0:
                # 字符串转json
                body_obj = json.loads(body)
                print("json:", body_obj)
                # 将摄像头设置为采集中状态
                status = 1
                # 获取patientid
                patientid = body_obj['patientId']
                # 获取caseid
                caseid = body_obj['caseId']
                # 获取当前时间戳
                now = datetime.datetime.now()
                # 格式化时间戳
                otherStyleTime = now.strftime("%Y%m%d%H%M%S")
                # 创建本次采样的路径
                file_path = './img/' + patientid + '_' + caseid + '_' + otherStyleTime + '/'
                # 创建文件夹
                res = mkdir(file_path)
                print(res)
                print(file_path)
                # 采集20对深度图和rgb图
                for i in range(capture_number):
                    # 获取深度图和rgb图
                    color_image, depth_image = global_nd_rgb, global_nd_depth
                    # 创建16图像writer
                    writer16 = png.Writer(width=depth_image.shape[1], height=depth_image.shape[0],
                                          bitdepth=16, greyscale=True)
                    # 保存rgb图
                    cv2.imwrite(file_path + str(i) + '_rgb.jpg', color_image)
                    # 保存16位深度图
                    with open(file_path + str(i) + '_depth.jpg', 'wb') as f:
                        zgray2list = depth_image.tolist()
                        writer16.write(f, zgray2list)
                status = 0
        except:
            print('error')
            status = 2
    # 创建一个json对象
    json_obj = {}
    # json返回的status为当前全局status
    json_obj['status'] = status
    # json对象转json字符串
    json_str = json.dumps(json_obj)
    # 计算总包长
    total_len = len(bytes(json_str, encoding='utf-8')) + 12
    length_bytes = struct.pack("<i", total_len)
    # 拼接字节
    content = headCode + length_bytes + MSG_id_bytes + Crc_test + Reserved_test + bytes(json_str, encoding='utf-8')
    return content

def write_start_log():
    file_path = "./log"
    file = open(file_path, 'w')
    # 获取当前时间戳
    now = datetime.datetime.now()
    # 格式化时间戳
    otherStyleTime = now.strftime("%Y-%m-%d %H:%M:%S")
    file.write(otherStyleTime)
    file.close()

def camera_threading():
    print('sub-thread start')
    global global_nd_rgb, global_nd_depth
    try:
        # 创建管道
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
        while True:
            if STOP_SIG:
                print('thread exit')
                exit()
            global_nd_rgb, global_nd_depth = get_aligned_images(pipeline, align)
    except:
        print("camera connect fail")
        exit()

# 主函数
if __name__ == '__main__':
    thread1 = Thread(target=camera_threading)
    thread1.start()
    # write_start_log()
    # socket部分
    s = socket.socket()
    # --------------测试---------------
    # host = '127.0.0.1'
    # --------------测试---------------
    # 获取局域网ip
    host = gethostbyname(gethostname())
    print('host:', host)
    port = 60000
    s.bind((host, port))
    s.listen(5)
    print('start')
    while True:
        if type(global_nd_rgb) == np.ndarray:
            if FIRST_TIPS:
                print('camera initialization successful')
                FIRST_TIPS = False
            try:
                c, addr = s.accept()
                print(addr, " connected")
                counter = 0
                while True:
                    try:
                        all_data = c.recv(12)
                        if len(all_data) > 0:
                            # 设置为bytearray
                            rec_data = bytearray(all_data)
                            print(rec_data)
                            # 获取headCode
                            head_index = all_data.find(b'\xff\xff\xff\xff')
                            # 如果headCode在第一位，代表是一个数据包的开始
                            if head_index == 0:
                                # 获取当前数据长度
                                curSize = len(all_data)
                                # 获取整个数据包的长度，Length部分
                                allLen = int.from_bytes(rec_data[head_index + 4:head_index + 8], byteorder='little')
                                # 如果当前长度还没达到数据包的长度
                                while curSize < allLen:
                                    # 继续获取数据
                                    data = c.recv(1024)
                                    # 将新的数据拼接到当前数据包末尾
                                    all_data += data
                                    # 更新数据包长度
                                    curSize += len(data)
                                content = get_return(all_data)
                                print(content)
                                # 返回结果信息
                                c.send(content)
                    except Exception as e:
                        # print("error-2l", e)
                        c.close()
                        print(addr, " disconnected")
                        break
            except Exception as e:
                # print("error-1l", e)
                continue
    STOP_SIG = True
    s.close()
