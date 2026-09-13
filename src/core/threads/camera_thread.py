"""相机推流线程 —— 常驻运行，持续采集帧并推送 FrameBuffer + UI 预览。

职责：
- 循环调 camera.grab_frame()
- 推入 FrameBuffer（供检测 Worker 消费）
- 转 QImage 发射 preview_ready 信号（给 UI 主线程贴图）
- 按 preview_fps 限速
"""

import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from src.core.threads.frame_buffer import FrameBuffer


class CameraThread(QThread):
    """相机推流线程。

    信号（跨线程安全）：
        preview_ready(QImage, float)  — 预览帧 + 时间戳，UI 主线程接收
        error(str)                    — 采集异常
        fps_update(float)             — 实际帧率
    """

    preview_ready = Signal(QImage, float)
    error = Signal(str)
    fps_update = Signal(float)

    def __init__(self, camera, frame_buffer, parent=None):
        super().__init__(parent)
        self._camera = camera
        self._buffer = frame_buffer
        self._running = False
        self._fps_limit = 15          # 默认 15 fps 预览
        self._resize_to = None        # (w, h) 可选降采样

    def set_fps_limit(self, fps):
        """设置预览帧率上限，0 表示不限。"""
        self._fps_limit = max(0, fps)

    def set_resize(self, width, height):
        """预览缩放（减少 QImage 开销）。"""
        if width and height:
            self._resize_to = (width, height)
        else:
            self._resize_to = None

    def stop(self):
        """通知线程退出（不阻塞）。"""
        self._running = False

    def run(self):
        """主循环。"""
        self._running = True
        interval = 1.0 / self._fps_limit if self._fps_limit > 0 else 0
        last_tick = 0
        fps_counter = 0
        fps_timer = time.time()

        while self._running:
            now = time.time()
            if interval > 0 and (now - last_tick) < interval:
                self.msleep(max(1, int((interval - (now - last_tick)) * 1000)))
                continue

            t0 = time.time()
            frame = self._camera.grab_frame()
            if frame is None:
                self.msleep(10)
                continue

            ts = time.time()
            last_tick = ts

            # 推入帧缓冲
            self._buffer.put(frame, ts)

            # 转 QImage 并发射预览信号
            preview = self._bgr_to_qimage(frame)
            if preview is not None:
                self.preview_ready.emit(preview, ts)

            # FPS 统计
            fps_counter += 1
            if ts - fps_timer >= 1.0:
                self.fps_update.emit(fps_counter / (ts - fps_timer))
                fps_counter = 0
                fps_timer = ts

    # ── 内部 ────────────────────────────────────────────

    def _bgr_to_qimage(self, frame):
        """BGR ndarray → RGB QImage（可降采样）。"""
        try:
            img = frame
            if self._resize_to:
                img = cv2.resize(img, self._resize_to, interpolation=cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            return QImage(rgb.data, w, h, w * ch, QImage.Format_RGB888)
        except Exception as e:
            self.error.emit(f"帧转换失败：{e}")
            return None
