#!/usr/bin/env python3
"""
简化版棋盘生成器 - 只需要OpenCV
适合你当前的环境配置
"""

import numpy as np
import cv2
import os
from datetime import datetime
import argparse

def generate_checkerboard_for_a4(rows=8, cols=11, square_size_mm=18, margin_mm=15):
    """
    生成适合A4纸打印的棋盘
    
    Args:
        rows: 棋盘行数（格子数量）
        cols: 棋盘列数（格子数量）  
        square_size_mm: 每个格子的尺寸(mm)
        margin_mm: 边距(mm)
    
    Returns:
        生成的文件路径和内角点数量
    """
    # A4纸尺寸和DPI设置
    a4_width_mm = 210
    a4_height_mm = 297
    dpi = 300
    
    # 转换为像素
    a4_width_px = int(a4_width_mm * dpi / 25.4)
    a4_height_px = int(a4_height_mm * dpi / 25.4)
    square_size_px = int(square_size_mm * dpi / 25.4)
    margin_px = int(margin_mm * dpi / 25.4)
    
    # 计算棋盘尺寸
    board_width = cols * square_size_px
    board_height = rows * square_size_px
    
    # 检查是否适合A4纸
    total_width = board_width + 2 * margin_px
    total_height = board_height + 2 * margin_px
    
    if total_width > a4_width_px or total_height > a4_height_px:
        print(f"警告: 棋盘尺寸可能超出A4纸范围!")
        print(f"当前: {total_width//dpi*25.4:.1f}mm x {total_height//dpi*25.4:.1f}mm")
        print(f"A4纸: {a4_width_mm}mm x {a4_height_mm}mm")
    
    # 创建白色背景
    img = np.ones((a4_height_px, a4_width_px), dtype=np.uint8) * 255
    
    # 计算棋盘在A4纸上的起始位置（居中）
    start_x = (a4_width_px - board_width) // 2
    start_y = (a4_height_px - board_height) // 2
    
    # 绘制棋盘
    for row in range(rows):
        for col in range(cols):
            # 黑白交替，确保左上角是黑色
            if (row + col) % 2 == 0:
                color = 0  # 黑色
            else:
                color = 255  # 白色
            
            # 计算格子位置
            x1 = start_x + col * square_size_px
            y1 = start_y + row * square_size_px
            x2 = x1 + square_size_px
            y2 = y1 + square_size_px
            
            # 填充格子
            img[y1:y2, x1:x2] = color
    
    # 添加信息文字
    info_text = f"{cols}x{rows} squares, {square_size_mm}mm each"
    cv2.putText(img, info_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
    
    corners_text = f"Inner corners: {cols-1}x{rows-1}"
    cv2.putText(img, corners_text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, 0, 2)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"checkerboard_{cols}x{rows}_{square_size_mm}mm_{timestamp}.png"
    
    # 保存图像
    cv2.imwrite(filename, img)
    
    # 计算内角点数量
    inner_corners = (cols - 1, rows - 1)
    
    print(f"棋盘已生成: {filename}")
    print(f"  - 格子数量: {cols} x {rows}")
    print(f"  - 内角点数量: {inner_corners[0]} x {inner_corners[1]}")
    print(f"  - 格子尺寸: {square_size_mm}mm")
    print(f"  - 在camera_calibration.py中使用:")
    print(f"    checkerboard_size={inner_corners}")
    print(f"    square_size={square_size_mm}.0")
    
    return filename, inner_corners

def main():
    """命令行入口：生成 A4 棋盘（默认推荐配置，可用参数覆盖）。"""
    parser = argparse.ArgumentParser(description="简化版相机标定棋盘生成器")
    parser.add_argument("--cols", type=int, default=8, help="列数（格子数量）")
    parser.add_argument("--rows", type=int, default=11, help="行数（格子数量）")
    parser.add_argument("--size", type=float, default=18.0, help="格子尺寸(mm)")
    args = parser.parse_args()

    filename, corners = generate_checkerboard_for_a4(args.rows, args.cols, args.size, 15)
    print(f"\n请更新你的 camera_calibration.py:")
    print(f"checkerboard_size={corners}")
    print(f"square_size={args.size}")

    print("\n" + "=" * 40)
    print("打印说明:")
    print("1. 打印时选择 '实际尺寸' 或 '100%' 缩放")
    print("2. 使用高质量打印设置")
    print("3. 打印在较厚的纸上或贴在平板上")
    print("4. 打印后用尺子测量几个格子确认尺寸正确")
    print("5. 如果尺寸不对，需要更新代码中的square_size参数")

    print(f"\n生成的文件: {filename}")
    print("可以直接用于A4纸打印！")

if __name__ == "__main__":
    main()
