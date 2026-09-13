# tools/ - 工具脚本

## 目录说明
存放项目的**辅助工具脚本**（校准、测试、调试等）。

这些脚本不是主程序的一部分，但在开发、调试、校准过程中很有用。

---


---

## 使用方法

### 运行单个工具
```bash
# 计算像素比例（基于标定内参，方法1）
D:\Miniconda Settings\envs\imageprocessing\python.exe tools/scale.py

# 相机标定 / 畸变矫正
D:\Miniconda Settings\envs\imageprocessing\python.exe tools/calib.py

# 测试串口
D:\Miniconda Settings\envs\imageprocessing\python.exe tools/serial_test.py
```

### 查看工具说明
每个脚本都有 `--help` 参数：
```bash
D:\Miniconda Settings\envs\imageprocessing\python.exe tools/serial_test.py --help
```

---

## 工具详细说明

### scale.py
**功能**：基于相机标定内参计算 `pixel_per_mm`（每毫米对应的像素数），即「像素 ↔ 真实距离」换算比例。

**使用流程**：
1. 先运行 `calib.py` 完成标定，得到 `camera_calibration.pkl`
2. 运行脚本，它会读取 pkl 内参与你测量时的**工作距离**（默认 300mm）
3. 脚本用 `pixel_per_mm = 焦距 / 工作距离` 公式算出比例并写入配置

> 注意：`pixel_per_mm` 随工作距离变化（透视关系），请传入与实际测量一致的估计距离。

**输出**：更新 `config/app_settings.yaml` 中的 `pixel_per_mm` 值（保留其他键，四舍五入 4 位）。

---

### calib.py
**功能**：相机标定（校正镜头畸变），提高坐标转换精度。

**使用流程**：
1. 打印棋盘格图案（用 `generate_checkerboard.py` 生成）
2. 从不同角度拍摄 10-20 张棋盘格照片
3. 运行脚本，传入照片目录
4. 脚本检测角点并调用 `cv2.calibrateCamera` 计算内参

**输出**：`camera_calibration.pkl`（相机矩阵、畸变系数、棋盘尺寸、方格尺寸、图像尺寸）

**其它能力**：`undistort_image()` 畸变矫正、`test_undistortion` / `test_checkerboard_detection` 调试，以及通过 mvsdk 连实体相机实时采集（`capture_calibration_images`）。

---

### generate_checkerboard.py
**功能**：生成棋盘格图案（用于相机标定）。

**使用方式**：
```bash
D:\Miniconda Settings\envs\imageprocessing\python.exe tools/generate_checkerboard.py --rows 6 --cols 9 --size 50
```
- `--rows`: 棋盘格行数
- `--cols`: 棋盘格列数
- `--size`: 每个格子的大小（像素）

**输出**：`data/checkerboard.png`

---

### serial_test.py
**功能**：测试 Arduino 串口通信。

**使用方式**：
```bash
D:\Miniconda Settings\envs\imageprocessing\python.exe tools/serial_test.py --port COM3 --baudrate 115200
```

**测试内容**：
1. 连接串口
2. 发送 `v`（版本查询）
3. 发送 `?`（位置查询）
4. 发送 `B100`（继电器测试）
5. 输出 Arduino 响应

---

## 注意事项

### 1. 工具脚本需要单独安装依赖
某些工具可能需要额外的 Python 包（如 `numpy`、`opencv-python`），主程序不依赖这些包。

### 2. 工具脚本可能修改配置文件
某些工具（如 `scale.py`）会直接修改 `config/app_settings.yaml`。

**建议**：运行前备份配置文件。

### 3. 工具脚本路径问题
工具脚本可能需要从项目根目录运行（因为它们会导入 `config` 或 `src/core/`）。

**正确做法**：
```bash
cd C:\Users\chyun\Documents\AMyAllCode Files\python_demo2-master
D:\Miniconda Settings\envs\imageprocessing\python.exe tools\serial_test.py
```

---

### simple_checkerboard_generator.py
**功能**：轻量生成棋盘格图案（用于相机标定），作为 `generate_checkerboard.py` 的简化替代。

**使用方式**：
```bash
D:\Miniconda Settings\envs\imageprocessing\python.exe tools/simple_checkerboard_generator.py
```

**输出**：`data/checkerboard.png`（具体参数以脚本内默认值为准）

---

## 学习要点

### 1. 工具脚本的价值
- **快速验证**：不需要启动主程序就能测试某个功能
- **自动化校准**：减少手动计算错误
- **调试辅助**：快速定位问题

### 2. 工具脚本设计原则
- **单一职责**：每个脚本只做一件事
- **命令行参数**：用 `argparse` 解析参数
- **详细的帮助信息**：`--help` 要清楚

### 3. 工具脚本 vs 主程序
- **工具脚本**：开发/调试时用，不纳入最终部署
- **主程序**：用户使用的完整应用

---

## 相关文档
- `README.md` - 项目总览
- `config/README.md` - 配置说明
- `markdown_project/CODE_STYLE_GUIDE.md` - 代码风格

---

## 版本历史
- **2026-07-16**: 文件重命名 `camera_calibration.py`→`calib.py`、`calculate_pixel_mm_ratio.py`→`scale.py`；`scale.py` 仅保留方法1；修正 Python 路径为 `D:\Miniconda Settings\envs\imageprocessing\python.exe`；标定输出改为 `camera_calibration.pkl`
- **2026-06-21**: 从 `userTest/` 移入并整理
- **2025-10-09**: 初始版本
