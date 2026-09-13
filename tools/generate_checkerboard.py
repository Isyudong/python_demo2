#!/usr/bin/env python3
"""
相机标定棋盘生成器
生成适合A4纸打印的标定棋盘图案
"""

import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import os
from datetime import datetime
import argparse

class CheckerboardGenerator:
    def __init__(self):
        # A4纸尺寸 (210mm x 297mm)，转换为像素 (300DPI)
        self.a4_width_mm = 210
        self.a4_height_mm = 297
        self.dpi = 300
        
        # 计算A4纸的像素尺寸
        self.a4_width_px = int(self.a4_width_mm * self.dpi / 25.4)
        self.a4_height_px = int(self.a4_height_mm * self.dpi / 25.4)
        
        print(f"A4纸尺寸: {self.a4_width_px} x {self.a4_height_px} 像素")

    def generate_opencv_checkerboard(self, rows=8, cols=11, square_size_mm=20, margin_mm=10, save_path="checkerboard_opencv.png"):
        """
        使用OpenCV生成棋盘
        
        Args:
            rows: 棋盘行数（格子数量）
            cols: 棋盘列数（格子数量）
            square_size_mm: 每个格子的尺寸(mm)
            margin_mm: 边距(mm)
            save_path: 保存路径
        """
        # 确保参数类型正确
        rows = int(rows)
        cols = int(cols)
        square_size_mm = float(square_size_mm)
        margin_mm = float(margin_mm)
        
        # 转换为像素
        square_size_px = int(square_size_mm * self.dpi / 25.4)
        margin_px = int(margin_mm * self.dpi / 25.4)
        
        # 计算棋盘尺寸
        board_width = cols * square_size_px
        board_height = rows * square_size_px
        
        # 检查是否适合A4纸
        total_width = board_width + 2 * margin_px
        total_height = board_height + 2 * margin_px
        
        if total_width > self.a4_width_px or total_height > self.a4_height_px:
            print(f"警告: 棋盘尺寸 ({total_width}x{total_height}) 超出A4纸尺寸!")
            print(f"建议减小格子尺寸或格子数量")
            
            # 自动调整
            max_square_size_w = (self.a4_width_px - 2 * margin_px) // cols
            max_square_size_h = (self.a4_height_px - 2 * margin_px) // rows
            recommended_size = min(max_square_size_w, max_square_size_h)
            recommended_mm = recommended_size * 25.4 / self.dpi
            print(f"推荐格子尺寸: {recommended_mm:.1f}mm")
        
        # 创建白色背景
        img = np.ones((self.a4_height_px, self.a4_width_px), dtype=np.uint8) * 255
        
        # 计算棋盘在A4纸上的起始位置（居中）
        start_x = (self.a4_width_px - board_width) // 2
        start_y = (self.a4_height_px - board_height) // 2
        
        # 绘制棋盘
        for row in range(rows):
            for col in range(cols):
                # 黑白交替
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
        
        # 保存图像
        cv2.imwrite(save_path, img)
        
        # 计算内角点数量
        inner_corners_cols = cols - 1
        inner_corners_rows = rows - 1
        
        print(f"棋盘已生成: {save_path}")
        print(f"  - 格子数量: {cols} x {rows}")
        print(f"  - 内角点数量: {inner_corners_cols} x {inner_corners_rows}")
        print(f"  - 格子尺寸: {square_size_mm}mm")
        print(f"  - 棋盘尺寸: {board_width*25.4/self.dpi:.1f}mm x {board_height*25.4/self.dpi:.1f}mm")
        print(f"  - 在代码中使用: checkerboard_size=({inner_corners_cols}, {inner_corners_rows})")
        
        return save_path, (inner_corners_cols, inner_corners_rows)

    def generate_matplotlib_checkerboard(self, rows=8, cols=11, square_size_mm=20, save_path="checkerboard_matplotlib.pdf"):
        """
        使用Matplotlib生成高质量矢量棋盘(PDF格式)
        
        Args:
            rows: 棋盘行数（格子数量）
            cols: 棋盘列数（格子数量）
            square_size_mm: 每个格子的尺寸(mm)
            save_path: 保存路径
        """
        # 计算尺寸
        board_width_mm = cols * square_size_mm
        board_height_mm = rows * square_size_mm
        
        # 检查是否适合A4纸（留20mm边距）
        margin_mm = 20
        if board_width_mm + 2*margin_mm > self.a4_width_mm or board_height_mm + 2*margin_mm > self.a4_height_mm:
            print(f"警告: 棋盘尺寸超出A4纸!")
            max_size_w = (self.a4_width_mm - 2*margin_mm) / cols
            max_size_h = (self.a4_height_mm - 2*margin_mm) / rows
            recommended_size = min(max_size_w, max_size_h)
            print(f"推荐格子尺寸: {recommended_size:.1f}mm")
        
        # 创建图形
        fig_width = self.a4_width_mm / 25.4  # 转换为英寸
        fig_height = self.a4_height_mm / 25.4
        
        fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
        ax.set_xlim(0, self.a4_width_mm)
        ax.set_ylim(0, self.a4_height_mm)
        ax.set_aspect('equal')
        
        # 计算棋盘在A4纸上的起始位置（居中）
        start_x = (self.a4_width_mm - board_width_mm) / 2
        start_y = (self.a4_height_mm - board_height_mm) / 2
        
        # 绘制棋盘
        for row in range(rows):
            for col in range(cols):
                # 黑白交替
                if (row + col) % 2 == 0:
                    color = 'black'
                else:
                    color = 'white'
                
                # 计算格子位置（matplotlib坐标系，原点在左下角）
                x = start_x + col * square_size_mm
                y = start_y + (rows - 1 - row) * square_size_mm
                
                # 创建矩形
                rect = Rectangle((x, y), square_size_mm, square_size_mm, 
                               facecolor=color, edgecolor='black', linewidth=0.5)
                ax.add_patch(rect)
        
        # 添加标题和信息
        title_y = start_y + board_height_mm + 10
        ax.text(self.a4_width_mm/2, title_y, 
                f'Camera Calibration Checkerboard', 
                ha='center', va='bottom', fontsize=12, weight='bold')
        
        info_y = start_y - 15
        info_text = f'Size: {cols}×{rows} squares, {square_size_mm}mm each\nInner corners: {cols-1}×{rows-1}'
        ax.text(self.a4_width_mm/2, info_y, info_text, 
                ha='center', va='top', fontsize=10)
        
        # 移除坐标轴
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # 保存为PDF
        plt.savefig(save_path, format='pdf', bbox_inches='tight', 
                   pad_inches=0.1, dpi=300)
        plt.close()
        
        # 计算内角点数量
        inner_corners_cols = cols - 1
        inner_corners_rows = rows - 1
        
        print(f"矢量棋盘已生成: {save_path}")
        print(f"  - 格子数量: {cols} x {rows}")
        print(f"  - 内角点数量: {inner_corners_cols} x {inner_corners_rows}")
        print(f"  - 格子尺寸: {square_size_mm}mm")
        print(f"  - 在代码中使用: checkerboard_size=({inner_corners_cols}, {inner_corners_rows})")
        
        return save_path, (inner_corners_cols, inner_corners_rows)

    def generate_multiple_sizes(self):
        """
        生成多种尺寸的棋盘供选择
        """
        print("正在生成多种尺寸的标定棋盘...")
        
        # 不同的配置选项
        configs = [
            {"rows": 7, "cols": 10, "size": 20, "name": "standard_7x10_20mm"},
            {"rows": 8, "cols": 11, "size": 18, "name": "standard_8x11_18mm"},
            {"rows": 6, "cols": 9, "size": 25, "name": "large_6x9_25mm"},
            {"rows": 9, "cols": 12, "size": 15, "name": "small_9x12_15mm"},
        ]
        
        results = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for config in configs:
            # PNG版本（用于预览和程序测试）
            png_path = f"checkerboard_{config['name']}_{timestamp}.png"
            png_result = self.generate_opencv_checkerboard(
                rows=config["rows"], 
                cols=config["cols"], 
                square_size_mm=config["size"],
                save_path=png_path
            )
            
            # PDF版本（用于高质量打印）
            pdf_path = f"checkerboard_{config['name']}_{timestamp}.pdf"
            try:
                pdf_result = self.generate_matplotlib_checkerboard(
                    rows=config["rows"], 
                    cols=config["cols"], 
                    square_size_mm=config["size"],
                    save_path=pdf_path
                )
                results.append({
                    "config": config,
                    "png_path": png_result[0],
                    "pdf_path": pdf_result[0],
                    "inner_corners": png_result[1]
                })
            except ImportError:
                print("警告: matplotlib未安装，跳过PDF生成")
                results.append({
                    "config": config,
                    "png_path": png_result[0],
                    "pdf_path": None,
                    "inner_corners": png_result[1]
                })
            
            print("-" * 50)
        
        return results

def main():
    """命令行入口：生成相机标定棋盘。"""
    parser = argparse.ArgumentParser(description="相机标定棋盘生成器")
    sub = parser.add_subparsers(dest="mode")

    p_custom = sub.add_parser("custom", help="自定义棋盘")
    p_custom.add_argument("--cols", type=int, default=11)
    p_custom.add_argument("--rows", type=int, default=8)
    p_custom.add_argument("--size", type=float, default=20.0)

    sub.add_parser("standard", help="生成多种标准尺寸")
    sub.add_parser("quick", help="快速生成推荐配置 (8x11, 18mm)")

    args = parser.parse_args()
    generator = CheckerboardGenerator()

    if args.mode == "custom":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        png_path = f"custom_checkerboard_{args.cols}x{args.rows}_{args.size}mm_{timestamp}.png"
        generator.generate_opencv_checkerboard(args.rows, args.cols, args.size, png_path)
        try:
            pdf_path = f"custom_checkerboard_{args.cols}x{args.rows}_{args.size}mm_{timestamp}.pdf"
            generator.generate_matplotlib_checkerboard(args.rows, args.cols, args.size, pdf_path)
        except ImportError:
            print("提示: 安装matplotlib可生成高质量PDF版本")

    elif args.mode == "standard":
        results = generator.generate_multiple_sizes()
        print("\n\n生成完成！文件列表:")
        print("=" * 60)
        for result in results:
            config = result["config"]
            corners = result["inner_corners"]
            print(f"配置: {config['rows']}x{config['cols']} 格子, {config['size']}mm")
            print(f"  内角点: {corners[0]}x{corners[1]}")
            print(f"  PNG文件: {result['png_path']}")
            if result['pdf_path']:
                print(f"  PDF文件: {result['pdf_path']}")
            print(f"  代码使用: checkerboard_size={corners}")
            print("-" * 40)

    else:  # quick 或未指定
        print("\n生成推荐配置棋盘（8x11格子，18mm）...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        png_path = f"recommended_checkerboard_{timestamp}.png"
        generator.generate_opencv_checkerboard(8, 11, 18, png_path)
        try:
            pdf_path = f"recommended_checkerboard_{timestamp}.pdf"
            generator.generate_matplotlib_checkerboard(8, 11, 18, pdf_path)
            print(f"\n推荐使用PDF文件进行打印: {pdf_path}")
        except ImportError:
            print(f"\n推荐使用PNG文件进行打印: {png_path}")
            print("提示: 安装matplotlib (pip install matplotlib) 可生成更高质量的PDF")

    print("\n打印建议:")
    print("1. 使用高质量打印机，选择'实际尺寸'或'100%缩放'")
    print("2. 使用厚一点的纸张或贴在硬板上")
    print("3. 确保打印后测量格子实际尺寸，更新代码中的square_size参数")
    print("4. 避免打印时的缩放，保持原始尺寸")

if __name__ == "__main__":
    main()
