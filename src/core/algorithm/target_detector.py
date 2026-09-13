"""
目标检测模块 — 霍夫圆检测与颜色筛选。
"""

import cv2
import numpy as np


DEFAULT_DETECTION_PARAMS = {
    'dp': 1.5,
    'min_dist': 16,
    'param1': 100,
    'param2': 8,
    'min_radius': 4,
    'max_radius': 5,
    'blur_radius': 1,
    'median_ksize': 3,
}

def detect_circles(image, detection_params=None, hsv_range=None, detector=None):
    """在 BGR 图像上做霍夫圆检测并按 HSV 筛选非黄次品，返回 {'circles', 'image'}。"""
    params = {**DEFAULT_DETECTION_PARAMS, **(detection_params or {})}

    if detector is None:
        detector = CircleDetector(detection_params=params, color_filter=hsv_range)
    else:
        detector.update_detection_params(params)
        detector.update_color_filter(hsv_range or {})

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    raw = detector.detect_circles(gray)
    annotated = image.copy()

    if raw is None:
        return {'circles': [], 'image': annotated}

    filtered = detector.filter_circles_by_color(raw, image)
    result_circles = [(x, y, r) for (x, y, r, valid) in filtered if valid]
    detector.draw_circles(annotated, filtered)

    return {'circles': result_circles, 'image': annotated}


class CircleDetector:
    """圆形目标检测器"""

    def __init__(self, detection_params=None, color_filter=None):
        self.detection_params = {**DEFAULT_DETECTION_PARAMS, **(detection_params or {})}
        self.color_filter = color_filter

    def detect_circles(self, gray_image):
        """在灰度图中检测圆形，返回 [(x, y, r), ...]，未检测到返回 None。"""
        # 中值滤波（去椒盐噪声）
        median_ksize = int(self.detection_params.get('median_ksize', 3) or 3)
        if median_ksize > 0:
            ksize = median_ksize if median_ksize % 2 == 1 else median_ksize + 1
            gray = cv2.medianBlur(gray_image, ksize)
        else:
            gray = gray_image

        # 高斯模糊预处理降噪（HoughCircles 内部 Canny 不做降噪，先模糊能减少误检）
        radius = int(self.detection_params.get('blur_radius', 0) or 0)
        if radius > 0:
            ksize = 2 * radius + 1
            gray = cv2.GaussianBlur(gray, (ksize, ksize), 0)

        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=self.detection_params.get('dp', DEFAULT_DETECTION_PARAMS['dp']),
            minDist=self.detection_params.get('min_dist', DEFAULT_DETECTION_PARAMS['min_dist']),
            param1=self.detection_params.get('param1', DEFAULT_DETECTION_PARAMS['param1']),
            param2=self.detection_params.get('param2', DEFAULT_DETECTION_PARAMS['param2']),
            minRadius=self.detection_params.get('min_radius', DEFAULT_DETECTION_PARAMS['min_radius']),
            maxRadius=self.detection_params.get('max_radius', DEFAULT_DETECTION_PARAMS['max_radius'])
        )

        if circles is not None:
            circles = np.round(circles[0]).astype("int")
            return circles
        return None

    def is_not_yellow_hsv(self, roi, mask):
        """根据 HSV 阈值判断 ROI 区域是否为非黄色"""
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mean_hsv = cv2.mean(hsv_roi, mask=mask)[:3]
        h, s, v = mean_hsv

        if self.color_filter:
            is_yellow = (
                self.color_filter['h_min'] <= h <= self.color_filter['h_max'] and
                s > self.color_filter['s_min'] and
                v > self.color_filter['v_min']
            )
            return not is_yellow
        return True  # 无颜色过滤时默认认为是目标

    def filter_circles_by_color(self, circles, roi, offset_x=0, offset_y=0):
        """根据颜色筛选圆形目标，返回 [(x, y, r, is_valid), ...]"""
        if circles is None:
            return []

        valid_circles = []

        for (cx, cy, r) in circles:
            mask = np.zeros(roi.shape[:2], dtype=np.uint8)
            cv2.circle(mask, (int(cx), int(cy)), int(r), 255, -1)

            is_valid = self.is_not_yellow_hsv(roi, mask)

            actual_x = cx + offset_x
            actual_y = cy + offset_y

            valid_circles.append((actual_x, actual_y, r, is_valid))

        return valid_circles

    def draw_circles(self, image, circles, offset_x=0, offset_y=0, color=(0, 0, 255), thickness=2):
        """在图像上绘制筛选后的圆形"""
        for (x, y, r, is_valid) in circles:
            if is_valid:
                roi_x = x - offset_x
                roi_y = y - offset_y
                cv2.circle(image, (int(roi_x), int(roi_y)), int(r), color, thickness)

    def update_detection_params(self, new_params):
        """更新检测参数"""
        self.detection_params.update(new_params)

    def update_color_filter(self, new_filter):
        """更新颜色筛选参数（整体替换，None 表示不筛选）"""
        self.color_filter = new_filter
