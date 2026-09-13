"""检测 Worker —— 一次性异步目标检测（QObject + moveToThread）。"""

import cv2
import numpy as np
from PySide6.QtCore import QObject, QThread, Signal, Slot

from src.core.algorithm.target_detector import detect_circles, CircleDetector
from src.core.messages import DetectionResult


class DetectionWorker(QObject):
    """一次性检测 Worker。

    - moveToThread 到临时 QThread
    - 完成后自动 quit → deleteLater
    """

    result_ready = Signal(object)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._detector = CircleDetector()

    @Slot(np.ndarray, object, object, float, object)
    def run(self, frame, detection_params, hsv_range, pixel_per_mm, converter):
        """执行检测（在 Worker 线程中运行）。

        frame: BGR ndarray
        detection_params: 检测参数字典
        hsv_range: HSV 过滤字典
        pixel_per_mm: px→mm 换算比
        converter: 坐标转换器（可选）
        """
        try:
            result = detect_circles(
                frame,
                detection_params=detection_params,
                hsv_range=hsv_range,
                detector=self._detector,
            )

            circles_pixel = result.get('circles', []) if result else []
            annotated_bgr = result.get('image', frame) if result else frame

            if converter is not None:
                circles_mm = [
                    converter.pixel_to_mm(x, y)
                    for x, y, r in circles_pixel
                ]
            else:
                circles_mm = [
                    (x / pixel_per_mm, y / pixel_per_mm)
                    for x, y, r in circles_pixel
                ]

            detection_result = DetectionResult(
                circles_pixel=circles_pixel,
                circles_mm=circles_mm,
                annotated_qimage=None,
                image_bgr=annotated_bgr,
            )

            self.result_ready.emit(detection_result)

        except Exception as e:
            self.error.emit(f"检测失败：{e}")
