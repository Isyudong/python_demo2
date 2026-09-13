"""
core 包 — 业务逻辑层
包含算法、工具类和流程控制器。
"""

from .algorithm.target_detector import detect_circles, CircleDetector
from .utils.coords import CoordConverter
from .utils.roi_manager import ROIManager

__all__ = [
    'detect_circles',
    'CircleDetector',
    'CoordConverter',
    'ROIManager',
]
