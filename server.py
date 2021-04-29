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
import time
from socket import gethostbyname, gethostname
from threading import Lock, Thread
socket.setdefaulttimeout(10)


# 请求头数据
pipeline = None
STORE_PATH = './img'
buffer = 1024
headCode = b'\xff\xff\xff\xff'
MSG_Heart = '0000'
MSG_Save = '0200'
MSG_Video_Save = '0400'
MSG_Video_Stop = '0600'
MSG_Backup = '0800'
MSG_Open_DepthCamera = '0a00'

MSG_Heart_Ack_Msg_id = b'\x01\x00'
MSG_Save_Ack_Msg_id = b'\x03\x00'
MSG_Save_Start_Ack = b'\x05\x00'
MSG_Save_Stop_Ack = b'\x07\x00'
MSG_Backup_Ack = b'\x09\x00'
MSG_Open_DepthCamera_Ack = b'\x0b\x00'
Crc_test = b'\x00'
Reserved_test = b'\x00'
capture_number = 1

status = 0

# 视频采集
global_nd_rgb = None
global_nd_depth = None
STOP_SIG = False
FIRST_TIPS = True
RECORD_STOP_SIG = False
FPS = 30.0
FILE_COUNTER = 0
CAMERA_IS_OPEN = False
BACKUP_IN_PROGRESS = False
CAPTURE_IN_PROGRESS = False
RECORD_IN_PROGRESS = False

def upload_files():
    global FILE_COUNTER, BACKUP_IN_PROGRESS
    BACKUP_IN_PROGRESS = True
    print("备份开始\n")
    try:
        sk = socket.socket()
        sk.connect(('172.18.6.8', 60000))
        for _, dirs, _ in os.walk(STORE_PATH):
            for dir in dirs:
                if dir != '':
                    path = os.path.join(STORE_PATH, dir)
                    for _, _, files in os.walk(path):
                        for file in files:
                            FILE_COUNTER += 1
        for _, dirs, _ in os.walk(STORE_PATH):
            for dir in dirs:
                if dir != '':
                    for _, _, files in os.walk(os.path.join(STORE_PATH, dir)):
                        for file in files:
                            send_file(sk, dir, file)
                            content = sk.recv(4)
                            try:
                                content = content.decode('utf-8')
                                if '0' in content:
                                    os.remove(os.path.join(STORE_PATH, dir, file))
                            except:
                                print("返回状态码异常", content)
                                continue
        content = '上传结束\n'
        print(content)
        FILE_COUNTER = 0
        BACKUP_IN_PROGRESS = False
    except:
        import traceback
        traceback.print_exc()
        BACKUP_IN_PROGRESS = False


def send_file(sk, file_path, filename):
    head = {'l': FILE_COUNTER,
            'filepath': file_path,
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
                f.close()
                break


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

def make_patient_dir(json_obj):
    # 获取patientid
    patientid = json_obj['patientId']
    # 获取caseid
    caseid = json_obj['caseId']
    # 获取当前时间戳
    now = datetime.datetime.now()
    # 格式化时间戳
    otherStyleTime = now.strftime("%Y%m%d%H%M%S")
    # 创建本次采样的路径
    file_path = STORE_PATH + '/' + str(patientid) + '_' + str(caseid) + '_' + str(otherStyleTime) + '/'
    # 创建文件夹
    return mkdir(file_path), file_path


# 获取返回结果
# data：数据包
# pipeline：intelrealsense管道
# align：对齐数据流对象
def get_return(data):
    global FIRST_TIPS, CAMERA_IS_OPEN
    # length: 96 bits
    # 使用全局的status变量
    global status, global_nd_rgb, global_nd_depth
    # 获取请求头
    header = data[:12]
    # 获取msg_id
    msg_id = header.hex()[16:20]
    if str(msg_id) != '0000':
        print(msg_id)
    MSG_id_bytes = MSG_Heart_Ack_Msg_id
    if CAMERA_IS_OPEN:
        if type(global_nd_rgb) == np.ndarray:
            if FIRST_TIPS:
                print('camera initialization successful')
                FIRST_TIPS = False
            else:
                status = 0
                global CAPTURE_IN_PROGRESS
                if msg_id == MSG_Save and CAPTURE_IN_PROGRESS is False:
                    CAPTURE_IN_PROGRESS = True
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
                            res, file_path = make_patient_dir(body_obj)
                            # 采集20对深度图和rgb图
                            for i in range(capture_number):
                                # 获取深度图和rgb图
                                color_image, depth_image = global_nd_rgb, global_nd_depth
                                # 创建16图像writer
                                writer16 = png.Writer(width=depth_image.shape[1], height=depth_image.shape[0],
                                                      bitdepth=16, greyscale=True)
                                print(file_path)
                                # 保存rgb图
                                cv2.imwrite(file_path + str(i) + '_rgb.jpg', color_image)
                                # 保存16位深度图
                                with open(file_path + str(i) + '_depth.jpg', 'wb') as f:
                                    zgray2list = depth_image.tolist()
                                    writer16.write(f, zgray2list)
                            status = 0
                        CAPTURE_IN_PROGRESS = False

                    except:
                        print('error')
                        import traceback
                        traceback.print_exc()
                        status = 0
                        CAPTURE_IN_PROGRESS = False
                elif msg_id == MSG_Video_Save:
                    MSG_id_bytes = MSG_Save_Start_Ack
                    if RECORD_IN_PROGRESS is False and CAMERA_IS_OPEN is True:
                        print("收到开始录制信号")
                        body = data[12:]
                        if len(body) > 0:
                            # 字符串转json
                            body_obj = json.loads(body)
                            print("json:", body_obj)
                            # 将摄像头设置为采集中状态
                            res, file_path = make_patient_dir(body_obj)
                            start_video_record(file_path)
                    else:
                        print("视频正在录制无法重复启动线程或摄像头未开启")
                elif msg_id == MSG_Video_Stop:
                    if RECORD_IN_PROGRESS:
                        global RECORD_STOP_SIG
                        MSG_id_bytes = MSG_Save_Stop_Ack
                        RECORD_STOP_SIG = True
                        print("收到录制结束信号")
                    else:
                        print("不在录制状态下，无法结束录制")
    else:
        status = 4
    if msg_id == MSG_Open_DepthCamera:
        if CAMERA_IS_OPEN == False:
            thread1 = Thread(target=camera_threading)
            thread1.start()
            status = 0
            CAMERA_IS_OPEN = True
        else:
            print("摄像头已开启")
    if msg_id == MSG_Backup:
            if CAMERA_IS_OPEN and BACKUP_IN_PROGRESS is False and RECORD_IN_PROGRESS is False:
                MSG_id_bytes = MSG_Backup_Ack
                thread_backup = Thread(target=upload_files)
                thread_backup.start()
            else:
                print("系统正在备份")
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

def start_video_record(path):
    thread = Thread(target=video_record_threading, args=(path,))
    thread.start()

def video_record_threading(path):
    global RECORD_STOP_SIG, RECORD_IN_PROGRESS
    RECORD_IN_PROGRESS = True
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    t = time.time()
    out = cv2.VideoWriter(os.path.join(path, str(t) + '.avi'), fourcc, 30, (640, 480))
    try:
        ts = datetime.datetime.now()
        while True:
            if RECORD_STOP_SIG:
                break
            te = datetime.datetime.now()
            sec = te - ts
            if int(sec.seconds) > 300:
                print(sec.seconds)
                print("五分钟时间到，视频录制结束")
                break
            out.write(global_nd_rgb)
            # time.sleep(0.01)
        out.release()
        print("RECORD_STOP_SIG:", RECORD_STOP_SIG)
        print("RECORD_IN_PROGRESS:", RECORD_IN_PROGRESS)
        RECORD_STOP_SIG = False
        RECORD_IN_PROGRESS = False
        print("录制结束")
    except:
        import traceback
        traceback.print_exc()
        out.release()
        RECORD_STOP_SIG = False
        RECORD_IN_PROGRESS = False
        print("录制异常结束")

def camera_threading():
    print('sub-thread start')
    global global_nd_rgb, global_nd_depth, pipeline
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
                pipeline.stop()
                print('thread exit')
                break
            global_nd_rgb, global_nd_depth = get_aligned_images(pipeline, align)
    except:
        pipeline.stop()
        print("camera connect fail")
        exit()

# 主函数
if __name__ == '__main__':
    # write_start_log()
    # socket部分
    s = socket.socket()
    # --------------测试---------------
    # host = '127.0.0.1'
    # --------------测试---------------
    # 获取局域网ip
    host = "172.18.6.6"
    print('host:', host)
    port = 60000
    s.bind((host, port))
    s.listen(5)
    print('start')
    while True:
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
                        # print(rec_data)
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
                            # print(content)
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
    if pipeline is not None:
        pipeline.stop()
