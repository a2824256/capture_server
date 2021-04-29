import time
import datetime
ts = datetime.datetime.now()
while True:
    te = datetime.datetime.now()
    sec = te - ts
    # if int(sec.seconds) > 300:
    #     print("五分钟时间到，视频录制结束")
    #     break
    print(sec.seconds)