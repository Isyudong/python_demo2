# src/core/ - 业务逻辑层

## 📋 目录说明
存放项目的核心业务逻辑，包括工作流程、算法和工具类。

---

## 📁 子目录列表

### messages.py
**跨线程数据契约** - 定义线程间通信的消息数据结构
- `FrameMessage`: 相机帧（含时间戳、序号）
- `DetectionResult`: 检测结果（圆形列表、标注图像、耗时）
- `CommStatus`: 通信状态（连通/断开/错误）
- `CommRequest`: 协议指令请求（BATCH_START/TARGET/BATCH_COMPLETE/ABORT）
- `WriterTask`: 写盘任务（帧保存、结果保存）

### algorithm/
**算法模块** - 存放图像处理和分析算法
- `circle_detector.py`: 圆形检测器（霍夫圆变换）

### utils/
**工具类** - 存放辅助函数和工具类
- `coords.py`: 坐标转换器（像素坐标 ↔ 毫米坐标，全项目换算单一来源）
- `roi_manager.py`: ROI 管理器（感兴趣区域，支持加载/保存/绘制/校验，含行内注释与解析容错）

### workflow.py
**工作流程类** - 核心业务逻辑，协调设备和算法完成完整任务

---

## 🔧 主要功能

### Workflow 类 (`workflow.py`)
核心工作流程管理器，负责：
1. **设备管理**：启动/停止相机，连接/断开 Arduino
2. **图像采集**：单张采集或连续采集（实时预览）
3. **圆形检测**：调用 `detect_circles()` 检测图像中的圆形
4. **坐标转换**：将像素坐标转换为机械坐标
5. **运动控制**：控制 Arduino 移动到目标位置
6. **剔除执行**：触发电磁阀，吹走次品
7. **校准管理**：计算像素到毫米的比例
8. **参数管理**：保存/加载参数到 YAML 文件

---

## 📝 代码示例

### 使用 Workflow 类
```python
from src.core.workflow import Workflow

# 创建 Workflow 实例
workflow = Workflow(
    on_frame=lambda img: print("新帧"),
    on_log=lambda msg: print(msg),
    on_detection_result=lambda circles, img: print(f"检测到 {len(circles)} 个圆形")
)

# 启动相机
workflow.start_camera()

# 采集并检测
result = workflow.capture_and_detect()
if result:
    print(f"检测到 {len(result['circles'])} 个次品目标")

# 执行剔除
workflow.eject_target(duration_ms=200)

# 断开连接
workflow.disconnect_arduino()
workflow.stop_camera()
```

---

### 坐标转换
```python
from src.core.utils.coords import CoordConverter

converter = CoordConverter(pixels_per_mm=4.4)
x_mm, y_mm = converter.pixels_to_mm((100, 200))
print(f"毫米坐标: ({x_mm}, {y_mm})")
```

---

### 圆形检测
```python
from src.core.algorithm.circle_detector import detect_circles
import cv2

image = cv2.imread('test.jpg')
result = detect_circles(image)

if result and result.get('circles'):
    circles = result['circles']
    annotated_image = result['image']
    print(f"检测到 {len(circles)} 个圆形")
```

---

## ⚠️ 注意事项

### 1. `grab_frame()` 直接返回 numpy 数组
**之前**（过度设计）：
```python
# 返回 CameraFrame 对象
frame_obj = camera.grab_frame()
img = frame_obj.image.copy()  # 还要 .image 才能拿到图像
```

**之后**（简单直接）：
```python
# 直接返回 numpy 数组
frame = camera.grab_frame()
img = frame.copy()  # 直接用
```

---

### 2. `get_motor_position()` 返回字典
**之前**（过度设计）：
```python
# 返回 MotorPosition 对象
pos_obj = arduino.get_position()
x = pos_obj.x
y = pos_obj.y
```

**之后**（简单直接）：
```python
# 返回字典
pos_dict = arduino.get_position()
x = pos_dict['x']
y = pos_dict['y']
```

---

### 3. Workflow 类通过回调函数与 UI 层通信
```python
workflow = Workflow(
    on_frame=lambda img: ...,           # 新帧回调
    on_log=lambda msg: ...,             # 日志回调
    on_detection_result=lambda c, img: ...  # 检测结果回调
)
```

**好处**：避免直接依赖 UI，实现松耦合。

---

## 🎓 学习要点

### 1. 单层职责
业务逻辑层不关心 UI 和硬件细节：
- UI 层负责显示和交互
- 设备层负责硬件通信
- 业务逻辑层负责协调设备和算法

---

### 2. 回调机制
通过回调函数通知上层（UI），实现松耦合：
```python
# Workflow 类
if self._on_frame:
    self._on_frame(img)  # 回调帧到 UI 显示
```

```python
# UI 层
def on_new_frame(self, img):
    """接收新帧，显示在界面上"""
    self.image_label.setPixmap(QPixmap.fromImage(img))
```

---

### 3. 状态管理
`Workflow` 类管理整个工作流程的状态：
- 相机是否启动
- 是否正在检测
- Arduino 是否连接
- 当前模式（sim/real）

---

### 4. 算法封装
将复杂算法（霍夫圆变换）封装成独立模块：
```python
# algorithm/circle_detector.py
def detect_circles(img, detection_params=None, hsv_range=None):
    """检测圆形，返回结果字典"""
    # ... 算法实现
    return {'circles': circles, 'image': annotated}
```

**好处**：
- 算法可以独立测试
- 算法可以独立优化
- 业务逻辑代码清晰易读

---

## 📖 相关文档
- `../README.md` - 项目总览
- `../../config/README.md` - 配置系统
- `../devices/README.md` - 设备层
- `../ui/README.md` - UI 层

---

## 📝 版本历史
- **2026-07-17**: 新增 messages.py（跨线程数据契约：FrameMessage/DetectionResult/CommStatus/CommRequest/WriterTask）
- **2026-07-16**: 坐标转换器文件名 coordinate_converter.py→coords.py、类 CoordinateConverter→CoordConverter；坐标转换示例更新为新 API（pixels_to_mm 接收 (x,y) 元组）；roi_manager 补充能力说明
- **2026-06-21**: 简化代码示例，删除过度设计
- **2026-06-21**: 重构项目，应用 4 层隔离架构
- **2025-10-09**: 初始版本
