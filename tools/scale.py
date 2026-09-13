#!/usr/bin/env python3
"""
像素与实际距离比例计算（功能二·像素对应真实距离）。

读取相机标定 pkl 的内参，基于棋盘格标定 + 假设工作距离，计算
pixel_per_mm 比例并写入 config/app_settings.yaml。

- pkl 读取复用 tools/calib.py 的 load_calibration_data（单一来源）。
- 像素↔毫米换算复用 src/core/utils/coords.py 的 CoordConverter（单一来源）。
"""

import sys
import argparse
import math
from pathlib import Path
from calib import load_calibration_data
from src.core.utils.coords import CoordConverter


class PixelScale:
    def __init__(self, calibration_file="camera_calibration.pkl"):
        """
        初始化像素-毫米比例计算器

        Args:
            calibration_file: 相机标定文件路径
        """
        self.calibration_file = calibration_file
        self.camera_matrix = None
        self.dist_coeffs = None
        self.checkerboard_size = None
        self.square_size = None
        self.img_size = None

        # 加载标定数据
        self.load_calibration_data()

    def load_calibration_data(self):
        """加载相机标定数据（pkl 读取复用 calib.load_calibration_data）"""
        try:
            calibration_data = load_calibration_data(self.calibration_file)

            self.camera_matrix = calibration_data['camera_matrix']
            self.dist_coeffs = calibration_data['dist_coeffs']
            self.checkerboard_size = calibration_data.get('checkerboard_size', (10, 7))
            self.square_size = calibration_data.get('square_size', 18.0)
            self.img_size = calibration_data['img_size']

            print(f"  标定数据加载成功")
            print(f"  - 图像尺寸: {self.img_size}")
            print(f"  - 方格大小: {self.square_size}mm")
            print(f"  - 棋盘尺寸: {self.checkerboard_size}")

            # 计算相机参数
            self.focal_length_x = self.camera_matrix[0, 0]
            self.focal_length_y = self.camera_matrix[1, 1]
            self.principal_point_x = self.camera_matrix[0, 2]
            self.principal_point_y = self.camera_matrix[1, 2]

            print(f"  - 焦距 fx: {self.focal_length_x:.2f} pixels")
            print(f"  - 焦距 fy: {self.focal_length_y:.2f} pixels")
            print(f"  - 主点: ({self.principal_point_x:.2f}, {self.principal_point_y:.2f})")

            return True

        except Exception as e:
            print(f"  加载标定数据失败: {e}")
            return False

    def calculate_ratio_from_checkerboard(self, estimated_distance=300.0):
        """
        基于棋盘格标定数据计算像素/毫米比例
        使用相机焦距和已知的棋盘格尺寸来计算平均比例

        注意: pixel_per_mm 随工作距离变化（透视关系）。estimated_distance
        为假设的相机到被测物工作距离(mm)，需与真实工作距离一致，否则比例有偏差。
        """
        if self.square_size is None:
            print("  缺少棋盘方格尺寸信息")
            return None

        # 计算每像素对应的物理尺寸（在估计距离处）
        pixel_size_x = estimated_distance / self.focal_length_x
        pixel_size_y = estimated_distance / self.focal_length_y

        print(f"\n=== 基于棋盘格标定的比例计算 ===")
        print(f"估计工作距离: {estimated_distance}mm")
        print(f"X方向像素尺寸: {pixel_size_x:.6f} mm/pixel")
        print(f"Y方向像素尺寸: {pixel_size_y:.6f} mm/pixel")
        print(f"平均像素尺寸: {(pixel_size_x + pixel_size_y)/2:.6f} mm/pixel")

        ratio_x = 1.0 / pixel_size_x  # pixels/mm
        ratio_y = 1.0 / pixel_size_y  # pixels/mm
        avg_ratio = (ratio_x + ratio_y) / 2

        print(f"X方向比例: {ratio_x:.2f} pixels/mm")
        print(f"Y方向比例: {ratio_y:.2f} pixels/mm")
        print(f"平均比例: {avg_ratio:.2f} pixels/mm")

        self.save_ratio_to_config(avg_ratio)

        return {
            'method': 'checkerboard_based',
            'distance_mm': estimated_distance,
            'pixel_size_x_mm': pixel_size_x,
            'pixel_size_y_mm': pixel_size_y,
            'ratio_x_pixels_per_mm': ratio_x,
            'ratio_y_pixels_per_mm': ratio_y,
            'avg_ratio_pixels_per_mm': avg_ratio
        }

    def distance_between_points(self, point1, point2):
        """
        计算两点之间的像素距离

        Args:
            point1: (x1, y1)
            point2: (x2, y2)
        """
        return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

    def pixel_to_mm(self, pixel_distance, ratio_pixels_per_mm):
        """
        将像素距离转换为毫米距离（复用 CoordConverter）

        Args:
            pixel_distance: 像素距离
            ratio_pixels_per_mm: 像素/毫米比例
        """
        return CoordConverter(ratio_pixels_per_mm).pixels_to_mm(pixel_distance)

    def mm_to_pixel(self, mm_distance, ratio_pixels_per_mm):
        """
        将毫米距离转换为像素距离（复用 CoordConverter）

        Args:
            mm_distance: 毫米距离
            ratio_pixels_per_mm: 像素/毫米比例
        """
        return CoordConverter(ratio_pixels_per_mm).mm_to_pixels(mm_distance)

    def save_ratio_to_config(self, ratio_pixels_per_mm, filename="config/app_settings.yaml"):
        """
        将计算出的像素/毫米比例写入配置文件（仅更新 pixel_per_mm 键，保留其他配置）

        Args:
            ratio_pixels_per_mm (float): 要写入的比例值
            filename (str): 配置文件路径
        """
        try:
            import yaml
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    cfg = yaml.safe_load(f) or {}
            except FileNotFoundError:
                cfg = {}
            cfg['pixel_per_mm'] = round(float(ratio_pixels_per_mm), 4)
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
            print(f"  已将 pixel_per_mm={cfg['pixel_per_mm']} 写入 {filename}")
        except Exception as e:
            print(f"  写入配置文件失败（请手动更新 pixel_per_mm）: {e}")


def main():
    """命令行入口：基于棋盘格标定数据计算像素-毫米比例。"""
    parser = argparse.ArgumentParser(description="像素-毫米比例计算")
    parser.add_argument("--distance", type=float, default=300.0,
                        help="估计工作距离(mm)，默认 300")
    args = parser.parse_args()

    calculator = PixelScale()
    if calculator.camera_matrix is None:
        print("无法加载相机标定数据，程序退出")
        return
    calculator.calculate_ratio_from_checkerboard(args.distance)


if __name__ == "__main__":
    main()
