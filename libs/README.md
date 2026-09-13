# libs/ - 第三方库

## 📋 目录说明
存放第三方库和 vendor 提供的 SDK 文件。

## 📁 子目录列表

### vendor_libs/
**Vendor 提供的库** - 硬件厂商提供的 SDK 或库文件
- `mvsdk.py`: 迈德威视相机 SDK 的 Python 封装

## 🔧 主要功能

### mvsdk.py
迈德威视相机的 Python SDK，提供：
- 相机初始化和配置
- 图像采集和处理
- 参数设置（曝光、增益等）

## 📝 使用方法

### 在代码中使用
```python
# 方式1：通过 pyproject.toml 安装后可自动发现（推荐）
# pip install -e .
# import 自动生效

# 方式2：手动添加路径（已废弃，不推荐）
# import sys
# sys.path.insert(0, 'libs/vendor_libs')

import mvsdk

# 初始化 SDK
ret = mvsdk.CameraSdkInit(1)

# 枚举相机
dev_list = mvsdk.CameraEnumerateDevice()

# 打开相机
h_camera = mvsdk.CameraInit(dev_list[0], -1, -1)

# 采集图像
p_raw_data, frame_head = mvsdk.CameraGetImageBuffer(h_camera, 200)
```

## ⚠️ 注意事项
- `mvsdk.py` 需要配合迈德威视相机驱动使用
- 仿真模式下不需要此库
- 不要修改 vendor 库文件，更新时直接替换

## 🎓 学习要点
- **Vendor SDK 集成**：如何将硬件厂商的 SDK 集成到项目中
- **路径管理**：推荐通过 `pyproject.toml` + `pip install -e .` 管理，不再需要手动 `sys.path.insert`
- **封装层**：`src/devices/real_impl.py` 封装了 `mvsdk.py` 的调用
