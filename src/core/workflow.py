"""鱼卵剔除系统工作流协调器。

Phase 2：从上帝类降级为协调器。
- 设备生命周期：start/stop camera/arduino
- 线程生命周期：start/stop camera_thread/comm_thread/writer_thread
- 异步检测/传输/中止
- 配置存取 + 手动控制
"""

import yaml
from PySide6.QtCore import QThread

from src.core.threads.frame_buffer import FrameBuffer
from src.core.threads.camera_thread import CameraThread
from src.core.threads.comm_thread import CommThread
from src.core.threads.detection_worker import DetectionWorker
from src.core.threads.writer_thread import WriterThread
from src.core.messages import CommRequest, WriterTask
from src.devices import create_camera, create_arduino
from src.devices.interfaces import DeviceState
from config import get_config, set_mode, get_mode, save_config
from src.core.utils.coords import CoordConverter
from src.core.utils.roi_manager import ROIManager


class Workflow:
    """协调器：设备生命周期 + 线程生命周期 + 配置存取。"""

    def __init__(self, on_frame, on_log, on_detection_result):
        self._on_frame = on_frame
        self._on_log = on_log
        self._on_detection_result = on_detection_result

        self._camera = None
        self._arduino = None
        self._camera_running = False

        self._frame_buffer = FrameBuffer()
        self._camera_thread = None
        self._comm_thread = None
        self._writer_thread = None
        self._detect_thread = None

        cfg = get_config()
        self._converter = CoordConverter(pixels_per_mm=cfg.get('pixel_per_mm', 4.40))
        self._roi_manager = ROIManager(roi_file_path='data/roi.txt')
        self._last_circles = []
        self._last_annotated = None

    def _log(self, msg):
        if self._on_log:
            self._on_log(msg)

    @property
    def is_sim_mode(self):
        return get_mode() == 'sim'

    # ══════════════════════════════════════════════════════
    # 设备生命周期
    # ══════════════════════════════════════════════════════

    def start_camera(self):
        if self._camera is not None:
            self._log("相机已连接")
            return True
        self._log(f"正在连接相机（模式：{get_mode().upper()}）...")
        self._camera = create_camera()
        ok = self._camera.connect()
        if ok:
            info = self._camera.get_camera_info()
            self._log(f"相机连接成功：{info}")
        else:
            self._log("相机连接失败")
            self._camera = None
        return ok

    def stop_camera(self):
        self._camera_running = False
        if self._camera:
            self._camera.disconnect()
            self._camera = None
        self._log("相机已停止")

    def connect_arduino(self):
        if self._arduino is not None:
            self._log("下位机已连接")
            return True
        self._log(f"正在连接下位机（模式：{get_mode().upper()}）...")
        self._arduino = create_arduino(message_callback=self._on_log)
        ok = self._arduino.connect()
        if ok:
            self._log("下位机连接成功")
        else:
            self._log("下位机连接失败")
            self._arduino = None
        return ok

    def disconnect_arduino(self):
        if self._arduino:
            self._arduino.disconnect()
            self._arduino = None
        self._log("下位机已断开")

    # ══════════════════════════════════════════════════════
    # 线程生命周期（Phase 2 新增）
    # ══════════════════════════════════════════════════════

    def start_camera_thread(self):
        if self._camera_thread is not None:
            return
        if self._camera is None:
            self._log("请先连接相机")
            return
        cfg = get_config()
        fps = cfg.get('camera', {}).get('preview_fps', 15)
        self._camera_thread = CameraThread(self._camera, self._frame_buffer)
        self._camera_thread.set_fps_limit(fps)
        self._camera_thread.preview_ready.connect(
            lambda qimg, ts: self._on_frame and self._on_frame(qimg))
        self._camera_thread.error.connect(self._log)
        self._camera_thread.start()
        self._log("相机线程已启动")

    def stop_camera_thread(self):
        if self._camera_thread is None:
            return
        self._camera_thread.stop()
        self._camera_thread.wait(3000)
        self._camera_thread = None
        self._log("相机线程已停止")

    def start_comm_thread(self):
        if self._comm_thread is not None:
            return
        if self._arduino is None:
            self._log("请先连接下位机")
            return
        self._comm_thread = CommThread(self._arduino)
        self._comm_thread.status_updated.connect(self._on_comm_status)
        self._comm_thread.error.connect(self._log)
        self._comm_thread.start()
        self._log("通信线程已启动")

    def stop_comm_thread(self):
        if self._comm_thread is None:
            return
        self._comm_thread.stop()
        self._comm_thread.wait(3000)
        self._comm_thread = None
        self._log("通信线程已停止")

    def start_writer_thread(self):
        if self._writer_thread is not None:
            return
        self._writer_thread = WriterThread()
        self._writer_thread.error.connect(self._log)
        self._writer_thread.start()
        self._log("写盘线程已启动")

    def stop_writer_thread(self):
        if self._writer_thread is None:
            return
        self._writer_thread.stop()
        self._writer_thread = None
        self._log("写盘线程已停止")

    # ══════════════════════════════════════════════════════
    # 检测 / 传输 / 中止（Phase 2 新增）
    # ══════════════════════════════════════════════════════

    def trigger_detection(self):
        """异步触发一次检测：从 FrameBuffer 取帧 → DetectionWorker 线程。"""
        frame, _ = self._frame_buffer.get()
        if frame is None:
            self._log("无帧可用")
            return

        # 如果有还在跑的检测线程，先等它结束
        if self._detect_thread is not None and self._detect_thread.isRunning():
            self._log("检测进行中，跳过")
            return

        cfg = get_config()
        params = cfg.get('detection', {})
        hsv = cfg.get('hsv_filter', {})

        worker = DetectionWorker()
        thread = QThread(self)  # parent=self 绑定生命周期，避免 "destroyed while running"
        worker.moveToThread(thread)
        self._detect_thread = thread

        def on_result(result):
            self._last_circles = result.circles_pixel
            self._last_annotated = result.image_bgr
            n = len(result.circles_pixel)
            self._log(f"检测完成：{n} 个目标")
            if self._on_detection_result:
                self._on_detection_result(
                    result.circles_pixel, result.image_bgr, result.circles_mm)
            thread.quit()

        def on_finished():
            worker.deleteLater()
            thread.deleteLater()
            if self._detect_thread is thread:
                self._detect_thread = None

        worker.result_ready.connect(on_result)
        worker.error.connect(lambda msg: self._log(msg))
        thread.started.connect(
            lambda: worker.run(frame, params, hsv,
                              self._converter.pixels_per_mm, self._converter))
        thread.finished.connect(on_finished)
        thread.start()

    def send_targets(self, targets_mm):
        """向通信线程投递一批目标坐标。"""
        if self._comm_thread is None:
            self._log("通信线程未启动")
            return
        self._comm_thread.send(CommRequest('batch_send', targets_mm))

    def abort(self):
        """紧急中止，向通信线程投递 ABORT 请求。"""
        if self._comm_thread is None:
            self._log("通信线程未启动")
            return
        self._comm_thread.send(CommRequest('abort'))
        self._log("已发送中止指令")

    def request_frame(self):
        """从 FrameBuffer 同步取当前帧。"""
        return self._frame_buffer.get()

    def _on_comm_status(self, status):
        self._log(f"[通信] {status.phase}: {status.detail}")

    # ══════════════════════════════════════════════════════
    # 手动控制
    # ══════════════════════════════════════════════════════

    def jog_move(self, dx, dy):
        if self._arduino is None:
            self._log("请先连接下位机")
            return False
        return self._arduino.move_relative(dx, dy)

    def jog_move_absolute(self, x, y):
        if self._arduino is None:
            self._log("请先连接下位机")
            return False
        return self._arduino.move_absolute(x, y)

    def get_motor_position(self):
        if self._arduino is None:
            return None
        return self._arduino.get_position()

    def stop_motors(self):
        if self._arduino:
            self._arduino.stop_motors()
            self._log("电机已紧急停止")

    def reset_motors(self):
        if self._arduino:
            self._arduino.reset()
            self._log("电机已重置，位置归零")

    # ══════════════════════════════════════════════════════
    # 配置存取
    # ══════════════════════════════════════════════════════

    def run_calibration(self, pixel_points, real_points):
        if len(pixel_points) < 2 or len(pixel_points) != len(real_points):
            self._log("校准失败：需要至少 2 个点，且像素点和真实点数量相同")
            return False
        ratios = []
        for (px, py), (rx, ry) in zip(pixel_points, real_points):
            if rx == 0 or ry == 0:
                continue
            ratios.append(px / rx)
            ratios.append(py / ry)
        if not ratios:
            self._log("校准失败：坐标点无效")
            return False
        avg_ratio = sum(ratios) / len(ratios)
        self._converter.set_conversion_ratio(avg_ratio)
        self._log(f"校准完成：1 mm = {avg_ratio:.2f} pixels")
        return True

    def save_params(self, file_path):
        cfg = get_config()
        params = {
            'mode': cfg.get('mode', 'sim'),
            'pixel_per_mm': self._converter.pixels_per_mm,
            'detection': dict(cfg.get('detection', {})),
            'hsv_filter': dict(cfg.get('hsv_filter', {})),
            'logging': dict(cfg.get('logging', {})),
            'calibration': dict(cfg.get('calibration', {})),
            'simulation': dict(cfg.get('simulation', {})),
            'camera': dict(cfg.get('camera', {})),
            'serial': dict(cfg.get('serial', {})),
            'motor': dict(cfg.get('motor', {})),
        }
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(params, f, allow_unicode=True, sort_keys=False)
            self._log(f"参数已保存：{file_path}")
            return True
        except Exception as e:
            self._log(f"保存参数失败：{e}")
            return False

    def load_params(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                params = yaml.safe_load(f)
            if isinstance(params, dict):
                cfg = get_config()
                for key in ('detection', 'hsv_filter', 'logging', 'calibration',
                           'simulation', 'camera', 'serial', 'motor'):
                    if key in params and isinstance(params[key], dict):
                        cfg[key] = params[key]
                if 'mode' in params:
                    set_mode(params['mode'])
                if 'pixel_per_mm' in params:
                    self._converter.set_conversion_ratio(params['pixel_per_mm'])
                self._log(f"参数已加载：{file_path}")
                return True
        except Exception as e:
            self._log(f"加载参数失败：{e}")
            return False

    def load_rois(self, file_path=None):
        rois = self._roi_manager.load_rois(file_path)
        self._log(f"ROI 加载：{len(rois)} 个区域")
        return rois

    # ══════════════════════════════════════════════════════
    # 参数读写
    # ══════════════════════════════════════════════════════

    def get_detection_params(self):
        return get_config().get('detection', {})

    def set_detection_params(self, params):
        cfg = get_config()
        cfg['detection'] = params
        save_config()
        self._log("检测参数已更新")

    def get_hsv_params(self):
        return get_config().get('hsv_filter', {})

    def set_hsv_params(self, params):
        cfg = get_config()
        cfg['hsv_filter'] = params
        save_config()
        self._log("HSV 参数已更新")

    def set_exposure(self, exposure_ms):
        if self._camera:
            self._camera.set_exposure(exposure_ms)
            self._log(f"曝光时间已设置为 {exposure_ms} ms")

    def set_serial_config(self, port, baudrate):
        cfg = get_config()
        cfg['serial']['port'] = port
        cfg['serial']['baudrate'] = baudrate
        save_config()
        self._log(f"串口配置已更新：{port} @ {baudrate}")

    # ══════════════════════════════════════════════════════
    # 杂项
    # ══════════════════════════════════════════════════════

    def send_raw(self, command):
        if self._arduino is None:
            self._log("下位机未连接")
            return ""
        return self._arduino.send_raw(command)

    def get_roi_count(self):
        return self._roi_manager.get_roi_count()

    def clear_rois(self):
        self._roi_manager.clear_rois()
        self._log("ROI 已清空")

    def get_conversion_info(self):
        return self._converter.get_conversion_info()

    def query_motor_position(self):
        pos = self.get_motor_position()
        if pos:
            return {'x': pos.get('x', 0.0), 'y': pos.get('y', 0.0), 'z': pos.get('z', 0.0)}
        return None

    def auto_detect_hardware(self):
        set_mode('real')
        cam_ok = False
        ard_ok = False
        try:
            self._camera = create_camera()
            cam_ok = self._camera.connect()
        except Exception as e:
            self._log(f"相机检测失败：{e}")
            cam_ok = False
        if not cam_ok:
            self._camera = None
        try:
            self._arduino = create_arduino(message_callback=self._on_log)
            ard_ok = self._arduino.connect()
        except Exception as e:
            self._log(f"下位机检测失败：{e}")
            ard_ok = False
        if not ard_ok:
            self._arduino = None
        if not cam_ok or not ard_ok:
            if cam_ok:
                self._camera.disconnect()
                self._camera = None
            if ard_ok:
                self._arduino.disconnect()
                self._arduino = None
            set_mode('sim')
            self._camera = create_camera()
            self._camera.connect()
            self._arduino = create_arduino(message_callback=self._on_log)
            self._arduino.connect()
            missing = []
            if not cam_ok:
                missing.append("相机")
            if not ard_ok:
                missing.append("下位机")
            self._log(f"未检测到{'/'.join(missing)}，已切换到模拟模式")
        else:
            self._log("硬件检测完成：真实设备已连接")

    # ══════════════════════════════════════════════════════
    # 属性
    # ══════════════════════════════════════════════════════

    @property
    def is_camera_connected(self):
        return self._camera is not None and self._camera.get_state() != DeviceState.DISCONNECTED

    @property
    def is_arduino_connected(self):
        return self._arduino is not None and self._arduino.get_state() != DeviceState.DISCONNECTED

    @property
    def camera_running(self):
        return self._camera_running

    @property
    def last_circles(self):
        return self._last_circles

    @property
    def converter(self):
        return self._converter

    def start_live_view(self):
        self._camera_running = True
        self.start_camera_thread()

    def stop_live_view(self):
        self._camera_running = False
        self.stop_camera_thread()
