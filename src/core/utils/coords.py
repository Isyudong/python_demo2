"""
像素坐标与实际毫米坐标转换（换算原语，全项目单一来源）。
"""


class CoordConverter:
    """
    坐标转换器类。

    注意: 本转换器使用单一标量 pixels_per_mm 做线性换算，等价于假设
    "相机到被测物工作距离固定"且"X/Y 方向比例近似一致"。若实际工作距离
    变化，pixel_per_mm 会随之改变（透视关系），此时换算结果将产生系统性偏差，
    需重新标定或改用随距离变化的比例模型。
    """

    def __init__(self, pixels_per_mm=4.40):
        if pixels_per_mm <= 0:
            raise ValueError("pixels_per_mm 必须为正数")
        self.pixels_per_mm = pixels_per_mm

    def set_conversion_ratio(self, pixels_per_mm):
        if pixels_per_mm <= 0:
            raise ValueError("pixels_per_mm 必须为正数")
        self.pixels_per_mm = pixels_per_mm

    def pixels_to_mm(self, pixel_coord):
        """像素坐标 (x, y) 或标量转为毫米坐标。"""
        if isinstance(pixel_coord, (tuple, list)) and len(pixel_coord) == 2:
            x_pixel, y_pixel = pixel_coord
            x_mm = x_pixel / self.pixels_per_mm
            y_mm = y_pixel / self.pixels_per_mm
            return (x_mm, y_mm)
        elif isinstance(pixel_coord, (int, float)):
            return pixel_coord / self.pixels_per_mm
        else:
            raise ValueError("pixel_coord 必须为标量或长度为 2 的 (x, y)")

    def mm_to_pixels(self, mm_coord):
        """毫米坐标 (x, y) 或标量转为像素坐标。"""
        if isinstance(mm_coord, (tuple, list)) and len(mm_coord) == 2:
            x_mm, y_mm = mm_coord
            x_pixel = x_mm * self.pixels_per_mm
            y_pixel = y_mm * self.pixels_per_mm
            return (round(x_pixel), round(y_pixel))
        elif isinstance(mm_coord, (int, float)):
            return round(mm_coord * self.pixels_per_mm)
        else:
            raise ValueError("mm_coord 必须为标量或长度为 2 的 (x, y)")

    def get_conversion_info(self):
        return {
            'pixels_per_mm': self.pixels_per_mm,
            'mm_per_pixel': 1 / self.pixels_per_mm,
            'description': f"1mm = {self.pixels_per_mm} pixels, 1 pixel = {1/self.pixels_per_mm:.4f} mm"
        }
