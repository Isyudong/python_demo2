"""真实硬件实现。"""

import time

import numpy as np

from config import get_config
from src.devices.interfaces import DeviceState, DeviceBase

try:
    import serial
except ImportError:
    serial = None


class RealCamera:
    """MVSDK 工业相机。"""

    def __init__(self):
        self._state = DeviceState.DISCONNECTED
        self._h_camera = 0
        self._p_frame_buffer = None
        self._frame_buffer_size = 0
        self._mono_camera = False
        cfg = get_config()
        camera_cfg = cfg.get('camera', {})
        self._exposure_time = camera_cfg.get('exposure_time', 30000)

    def connect(self):
        try:
            import libs.vendor_libs.mvsdk as mvsdk

            ret = mvsdk.CameraSdkInit(1)
            if ret != 0:
                print(f"[RealCamera] SDK 初始化失败: {ret}")
                return False

            dev_list = mvsdk.CameraEnumerateDevice()
            n_dev = len(dev_list)
            if n_dev < 1:
                print("[RealCamera] 未找到相机设备")
                return False

            print(f"[RealCamera] 找到 {n_dev} 个相机设备:")
            for i, dev_info in enumerate(dev_list):
                print(f"  {i}: {dev_info.GetFriendlyName()} {dev_info.GetPortType()}")

            dev_info = dev_list[0] if n_dev > 0 else None
            if dev_info is None:
                return False

            self._h_camera = mvsdk.CameraInit(dev_info, -1, -1)
            if self._h_camera == 0:
                print("[RealCamera] 打开相机失败")
                return False

            cap = mvsdk.CameraGetCapability(self._h_camera)

            self._mono_camera = (cap.sIspCapacity.bMonoSensor != 0)

            if self._mono_camera:
                mvsdk.CameraSetIspOutFormat(self._h_camera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)
            else:
                mvsdk.CameraSetIspOutFormat(self._h_camera, mvsdk.CAMERA_MEDIA_TYPE_BGR8)

            # 切换成连续采集 + 手动曝光
            mvsdk.CameraSetTriggerMode(self._h_camera, 0)
            mvsdk.CameraSetAeState(self._h_camera, 0)
            mvsdk.CameraSetExposureTime(self._h_camera, self._exposure_time)

            mvsdk.CameraPlay(self._h_camera)

            self._frame_buffer_size = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if self._mono_camera else 3)
            self._p_frame_buffer = mvsdk.CameraAlignMalloc(self._frame_buffer_size, 16)

            self._state = DeviceState.IDLE
            print(f"[RealCamera] 连接成功 - 曝光时间: {self._exposure_time/1000}ms, 模式: {'黑白' if self._mono_camera else '彩色'}")
            return True

        except Exception as e:
            print(f"[RealCamera] 连接失败：{e}")
            self._h_camera = 0
            return False

    def disconnect(self):
        if self._h_camera != 0:
            try:
                import libs.vendor_libs.mvsdk as mvsdk
                mvsdk.CameraUnInit(self._h_camera)
                print("[RealCamera] 相机已关闭")
            except Exception as e:
                print(f"[RealCamera] 关闭相机失败：{e}")

            if self._p_frame_buffer is not None:
                try:
                    import libs.vendor_libs.mvsdk as mvsdk
                    mvsdk.CameraAlignFree(self._p_frame_buffer)
                    print("[RealCamera] 缓冲区已释放")
                except Exception as e:
                    print(f"[RealCamera] 释放缓冲区失败：{e}")

            self._h_camera = 0
            self._p_frame_buffer = None
            self._state = DeviceState.DISCONNECTED

    def grab_frame(self):
        if self._state == DeviceState.DISCONNECTED or self._h_camera == 0:
            return None
        self._state = DeviceState.BUSY
        try:
            import libs.vendor_libs.mvsdk as mvsdk

            p_raw_data, frame_head = mvsdk.CameraGetImageBuffer(self._h_camera, 200)
            mvsdk.CameraImageProcess(self._h_camera, p_raw_data, self._p_frame_buffer, frame_head)
            mvsdk.CameraReleaseImageBuffer(self._h_camera, p_raw_data)

            frame_data = (mvsdk.c_ubyte * frame_head.uBytes).from_address(self._p_frame_buffer)
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((frame_head.iHeight, frame_head.iWidth, 1 if frame_head.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

            # 设置了目标分辨率时调整尺寸
            try:
                cfg = get_config()
                camera_cfg = cfg.get('camera', {})
                target_resolution = camera_cfg.get('target_resolution')
                if target_resolution is not None:
                    import cv2
                    frame = cv2.resize(frame, target_resolution, interpolation=cv2.INTER_LINEAR)
            except Exception as e:
                print(f"[RealCamera] 调整分辨率失败：{e}")

            self._state = DeviceState.IDLE
            return frame

        except Exception as e:
            if "TIMEOUT" not in str(e).upper():
                print(f"[RealCamera] 采集失败：{e}")
            self._state = DeviceState.IDLE
            return None

    def set_exposure(self, exposure_ms):
        """设置曝光时间。"""
        if self._h_camera != 0:
            try:
                import libs.vendor_libs.mvsdk as mvsdk
                mvsdk.CameraSetExposureTime(self._h_camera, int(exposure_ms * 1000))
                self._exposure_time = int(exposure_ms * 1000)
            except Exception as e:
                print(f"[RealCamera] 设置曝光失败：{e}")

    def get_state(self) -> DeviceState:
        return self._state

    def get_camera_info(self):
        info = {'name': 'RealCamera', 'mode': 'real'}
        if self._h_camera != 0:
            try:
                import libs.vendor_libs.mvsdk as mvsdk
                info['mono_camera'] = self._mono_camera
                info['exposure_time'] = self._exposure_time
            except Exception as e:
                print(f"[RealCamera] 获取相机信息失败：{e}")
        return info


class RealArduino(DeviceBase):
    """Arduino 串口通信。"""

    def __init__(self, message_callback=None):
        super().__init__(message_callback)
        self._state = DeviceState.DISCONNECTED
        self._serial = None
        self._is_connected = False
        self._lock = None  # 线程锁，延迟导入

    def connect(self):
        try:
            if serial is None:
                self._log("[RealArduino] 连接失败：未安装 pyserial")
                return False
            cfg = get_config().get('serial', {})
            port = cfg.get('port', 'COM3')
            baudrate = cfg.get('baudrate', 115200)
            timeout = cfg.get('timeout', 5)

            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout,
                write_timeout=timeout,
            )

            # 等待 Arduino 重启完成
            time.sleep(2)

            self._serial.flushInput()
            self._serial.flushOutput()

            self._is_connected = True
            self._state = DeviceState.IDLE
            self._log(f"[RealArduino] 串口连接成功：{port}")
            return True

        except Exception as e:
            self._log(f"[RealArduino] 连接失败：{e}")
            self._serial = None
            self._is_connected = False
            return False

    def disconnect(self):
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception as e:
                self._log(f"[RealArduino] 串口关闭失败：{e}")
        self._serial = None
        self._is_connected = False
        self._state = DeviceState.DISCONNECTED
        self._log("[RealArduino] 串口已断开")

    def move_absolute(self, x, y, z=0.0):
        if not self._is_connected or not self._serial:
            return False
        self._state = DeviceState.BUSY
        cmd = f"G0 X{x:.1f} Y{y:.1f} Z{z:.1f}\n"
        try:
            self._log(f"[RealArduino] {cmd.strip()}")
            self._serial.write(cmd.encode('utf-8'))
            self._serial.flush()
            resp = self._wait_for_response(timeout=5)
            self._state = DeviceState.IDLE
            self._log(f"   {resp}")
            return resp is not None and 'OK' in resp.upper()
        except Exception as e:
            self._state = DeviceState.IDLE
            self._log(f"   指令失败：{e}")
            return False

    def move_relative(self, dx, dy, dz=0.0):
        if not self._is_connected or not self._serial:
            return False
        self._state = DeviceState.BUSY
        cmd = f"G1 X{dx:.1f} Y{dy:.1f} Z{dz:.1f}\n"
        try:
            self._log(f"[RealArduino] {cmd.strip()}")
            self._serial.write(cmd.encode('utf-8'))
            self._serial.flush()
            resp = self._wait_for_response(timeout=5)
            self._state = DeviceState.IDLE
            self._log(f"   {resp}")
            return resp is not None and 'OK' in resp.upper()
        except Exception as e:
            self._state = DeviceState.IDLE
            self._log(f"   指令失败：{e}")
            return False

    def get_position(self):
        if not self._is_connected or not self._serial:
            return None
        try:
            cmd = "?\n"
            self._serial.write(cmd.encode('utf-8'))
            self._serial.flush()
            resp = self._wait_for_response(timeout=2)

            # 解析 "X=1.0 Y=2.0 Z=0.0"
            pos = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'timestamp': time.time()}
            if resp:
                for part in resp.split():
                    if part.startswith('X='):
                        try:
                            pos['x'] = float(part[2:])
                        except ValueError:
                            continue
                    elif part.startswith('Y='):
                        try:
                            pos['y'] = float(part[2:])
                        except ValueError:
                            continue
                    elif part.startswith('Z='):
                        try:
                            pos['z'] = float(part[2:])
                        except ValueError:
                            continue
            return pos
        except Exception as e:
            self._log(f"[RealArduino] 查询位置失败：{e}")
            return None

    def stop_motors(self):
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(b"STOP\n")
                self._serial.flush()
            except Exception as e:
                self._log(f"停止失败：{e}")
        self._state = DeviceState.IDLE
        self._log("[RealArduino] 电机紧急停止")

    def reset(self):
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(b"RESET\n")
                self._serial.flush()
                self._wait_for_response(timeout=2)
            except Exception as e:
                self._log(f"重置失败：{e}")
        self._state = DeviceState.IDLE
        self._log("[RealArduino] 控制器重置")

    def get_state(self) -> DeviceState:
        return self._state

    def send_raw(self, command, timeout=5):
        if not self._is_connected or not self._serial:
            return ""
        try:
            cmd = command.strip() + "\n"
            self._log(f"[RealArduino] 发送原始指令：{command.strip()}")
            self._serial.write(cmd.encode('utf-8'))
            self._serial.flush()
            resp = self._wait_for_response(timeout=timeout)
            self._log(f"   {resp}")
            return resp or ""
        except Exception as e:
            self._log(f"   指令失败：{e}")
            return ""

    def send_with_retry(self, command, timeout=5, retries=2):
        """发送指令，超时自动重试。

        返回 (response, success)：success 为 True 表示得到有效应答，
        全部重试失败返回 ("", False)。
        """
        for attempt in range(retries + 1):
            resp = self.send_raw(command, timeout=timeout)
            if resp:
                return resp, True
            if attempt < retries:
                self._log(f"   超时，重试 {attempt + 1}/{retries}...")
                time.sleep(0.3)
        self._log(f"   全部 {retries} 次重试均超时")
        return "", False

    def blast_on(self, duration_ms=None):
        if not self._is_connected or not self._serial:
            return False
        if duration_ms is None:
            duration_ms = 200
        cmd = f"BLAST ON {duration_ms:.0f}\n"
        try:
            self._log(f"[RealArduino] 打开电磁阀（{duration_ms:.0f}ms）")
            self._serial.write(cmd.encode('utf-8'))
            self._serial.flush()
            resp = self._wait_for_response(timeout=2)
            self._log(f"   {resp}")
            return resp is not None and 'OK' in resp.upper()
        except Exception as e:
            self._log(f"   电磁阀打开失败：{e}")
            return False

    def blast_off(self):
        if not self._serial or not self._serial.is_open:
            return
        try:
            cmd = "BLAST OFF\n"
            self._log("[RealArduino] 关闭电磁阀")
            self._serial.write(cmd.encode('utf-8'))
            self._serial.flush()
            resp = self._wait_for_response(timeout=2)
            self._log(f"   {resp}")
        except Exception as e:
            self._log(f"   电磁阀关闭失败：{e}")


    def _wait_for_response(self, timeout=2):
        """等待串口回复。"""
        if not self._serial:
            return None
        try:
            start_time = time.time()
            response_buffer = ""
            while time.time() - start_time < timeout:
                if self._serial.in_waiting > 0:
                    char = self._serial.read(1).decode('utf-8')
                    response_buffer += char
                    if '\n' in response_buffer or '\r' in response_buffer:
                        lines = response_buffer.replace('\r', '\n').split('\n')
                        for line in lines[:-1]:
                            line = line.strip()
                            if line:
                                return line
                        response_buffer = lines[-1]
                time.sleep(0.005)
            if response_buffer.strip():
                return response_buffer.strip()
            return None
        except Exception as e:
            self._log(f"等待响应失败：{e}")
            return None
