"""
ROI（感兴趣区域）的加载、保存、绘制与验证。
"""

import cv2
import os


class ROIManager:
    """ROI管理器类"""

    def __init__(self, roi_file_path=None):
        self.roi_file_path = roi_file_path or "data/roi.txt"
        self.rois = []

    def load_rois(self, file_path=None):
        """从文件加载 ROI 区域，返回 [(x, y, w, h), ...]。"""
        if file_path:
            self.roi_file_path = file_path

        self.rois = []

        try:
            if not os.path.exists(self.roi_file_path):
                print(f"ROI文件不存在: {self.roi_file_path}")
                return self.rois

            with open(self.roi_file_path, "r") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip().rstrip(";")  # 去掉行末的分号和空白
                    # 支持行内注释：丢弃 # 及其后的内容
                    if '#' in line:
                        line = line[:line.index('#')].strip()
                    if not line or line.startswith('#'):  # 跳过空行和注释行
                        continue

                    # 逐ROI容错：单个ROI损坏不影响同行其它ROI
                    for roi_str in line.split(")("):
                        roi_str = roi_str.strip("()")  # 去掉括号
                        if not roi_str:
                            continue
                        try:
                            coords = list(map(int, roi_str.split(",")))
                        except ValueError as e:
                            print(f"ROI解析错误 (第{line_num}行): {roi_str} - {e}")
                            continue
                        if len(coords) == 4:
                            self.rois.append(tuple(coords))
                        else:
                            print(f"ROI格式错误 (第{line_num}行): {roi_str} - 需要4个坐标值")

            print(f"成功加载 {len(self.rois)} 个ROI区域")
            for i, roi in enumerate(self.rois):
                print(f"  ROI{i}: {roi}")

        except Exception as e:
            print(f"加载ROI文件时出错: {e}")

        return self.rois

    def save_rois(self, rois=None, file_path=None):
        """保存 ROI 到文件。传入的 rois / file_path 仅用于本次保存，不改内部状态。"""
        target_rois = rois if rois is not None else self.rois
        target_path = file_path or self.roi_file_path

        try:
            with open(target_path, "w") as file:
                file.write("# ROI配置文件\n")
                file.write("# 格式: (x,y,width,height)\n")
                file.write("# 可以在一行中定义多个ROI: (x1,y1,w1,h1)(x2,y2,w2,h2)\n")
                file.write("# 以#开头的行为注释行\n\n")

                if target_rois:
                    roi_strings = [f"({r[0]},{r[1]},{r[2]},{r[3]})" for r in target_rois]
                    file.write("".join(roi_strings) + ";\n")

            print(f"ROI已保存到: {target_path}")
            return True

        except Exception as e:
            print(f"保存ROI文件时出错: {e}")
            return False

    def add_roi(self, x, y, width, height):
        roi = (x, y, width, height)
        self.rois.append(roi)
        print(f"添加ROI: {roi}")

    def remove_roi(self, index):
        if 0 <= index < len(self.rois):
            removed_roi = self.rois.pop(index)
            print(f"删除ROI{index}: {removed_roi}")
            return True
        else:
            print(f"无效的ROI索引: {index}")
            return False

    def clear_rois(self):
        self.rois.clear()
        print("已清空所有ROI区域")

    def draw_rois(self, image, color=(0, 255, 0), thickness=2, show_labels=True):
        """在传入的 image 上原地绘制 ROI 区域。"""
        for i, (x, y, w, h) in enumerate(self.rois):
            cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)

            if show_labels:
                label = f"ROI{i}"
                text_x = x
                text_y = y - 10 if y > 20 else y + h + 20

                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(image, (text_x, text_y - text_h - 2), (text_x + text_w, text_y + 2), color, -1)

                cv2.putText(image, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    def get_roi_by_index(self, index):
        if 0 <= index < len(self.rois):
            return self.rois[index]
        return None

    def extract_roi_from_image(self, image, index):
        roi = self.get_roi_by_index(index)
        if roi is not None:
            x, y, w, h = roi
            return image[y:y + h, x:x + w].copy()  # 返回副本，避免修改原图
        return None

    def validate_rois(self, image_shape):
        """返回落在图像范围内的有效 ROI 索引列表。"""
        height, width = image_shape[:2]
        valid_indices = []

        for i, (x, y, w, h) in enumerate(self.rois):
            if (x >= 0 and y >= 0 and
                    x + w <= width and y + h <= height and
                    w > 0 and h > 0):
                valid_indices.append(i)
            else:
                print(f"警告: ROI{i} {(x, y, w, h)} 超出图像范围 {(width, height)}")

        return valid_indices

    def get_roi_count(self):
        return len(self.rois)

    def get_roi_info(self):
        return {
            'file_path': self.roi_file_path,
            'roi_count': len(self.rois),
            'rois': self.rois.copy()
        }
