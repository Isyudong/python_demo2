import serial

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)

try:
    while True:
        ser.write('s'.encode())  # 注意：发送的数据需要是字节类型
        response = ser.readline()  # 读取一行数据
        if response:  # 检查是否有数据返回
            print(response.decode('utf-8').strip())  # 解码并去除多余的换行符
except KeyboardInterrupt:  #输入ctrl+c程序停止
    print("程序已手动终止")
except serial.SerialException as e:
    print(f"串口异常: {e}")
finally:
    ser.close()
