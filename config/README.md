# config/ - 配置目录

## 📋 目录说明
存放项目的**所有配置文件**和**配置加载器**。

**这是项目唯一的配置目录**，包含：
- ✅ YAML 配置文件（应用配置 + 设备参数）
- ✅ Python 配置加载器（读取 YAML，提供简单接口）

---

## 📄 文件列表

| 文件 | 说明 | 推荐使用方式 |
|------|------|----------------|
| `app_settings.yaml` | 应用配置（业务逻辑参数） | 修改运行模式、检测参数、HSV 过滤 |
| `device_params.yaml` | 设备参数（硬件相关参数） | 修改串口配置、相机参数、电机参数 |
| `config.py` | 配置加载器（从 YAML 读取，提供函数接口） | `from config import get_config` ✅ |
| `__init__.py` | 配置包导出（推荐导入方式） | `from config import get_config` ✅ |
| `README.md` | 本文件 | - |

---

## 🔧 使用方法

### 方式 1：获取配置字典（✅ 推荐）
```python
from config import get_config, get_mode

# 获取所有配置
cfg = get_config()
print(f"运行模式: {get_mode()}")
print(f"像素比例: {cfg['pixel_per_mm']}")
print(f"串口端口: {cfg['serial']['port']}")
```

**好处**：简单直接，用字典访问配置，清晰易读。

---

### 方式 2：切换模式
```python
from config import set_mode

set_mode('real')  # 切换到真实硬件模式
set_mode('sim')    # 切换回仿真模式
```

**注意**：`set_mode()` 只修改内存中的配置，不会修改 YAML 文件。

---

## 📝 配置文件说明

### app_settings.yaml - 应用配置
**业务逻辑相关的参数**，修改后通常需要重启应用。

```yaml
# 运行模式: sim 或 real
mode: sim

# 像素到毫米的转换比例 (需要根据实际校准)
pixel_per_mm: 4.40

# 检测参数
detection:
  dp: 1.5
  min_dist: 20
  param1: 250
  param2: 14
  min_radius: 10
  max_radius: 20
  blur_radius: 1
  median_ksize: 3

# HSV 颜色过滤
hsv_filter:
  h_min: 14
  h_max: 170
  s_min: 100
  s_max: 255
  v_min: 180
  v_max: 255

# 预览/检测帧率
preview_fps: 15
detect_fps: 0

# 通信参数（超时、重试、心跳）
comm:
  timeout: 5.0
  retries: 2
  heartbeat_interval: 5

# 异步写盘
writer:
  max_queue: 50

# 日志配置
logging:
  enabled: true
  file: logs/system.log
  level: INFO

# 校准配置
calibration:
  enabled: false
  points: []

# 仿真参数
simulation:
  camera_delay: 0.1
  arduino_delay: 0.05
  image_width: 640
  image_height: 480
  noise_level: 0.0
  camera:
    image_dir: test_images
    frame_rate: 10
  arduino:
    move_delay: 0.3
    blast_delay: 0.2
```

---

### device_params.yaml - 设备参数
**硬件相关的参数**，修改后需要重新连接设备。

```yaml
# 串口配置 (Arduino)
serial:
  port: COM3           # 串口端口 (Windows) 或 /dev/ttyUSB0 (Linux)
  baudrate: 115200     # 波特率
  timeout: 5            # 读取超时 (秒)
  connection_timeout: 8  # 连接超时 (秒)
  retry_count: 3        # 重试次数

# 相机配置 (MindVision MVSDK)
camera:
  exposure_time: 30000   # 曝光时间 (微秒)
  target_resolution: null  # 目标分辨率 (null = 使用原始分辨率)
  # target_resolution: [1280, 960]  # 示例：缩放到 1280x960

# 电机参数 (步进电机)
motor:
  x_axis:
    steps_per_mm: 40     # X 轴步数/毫米
    max_speed: 2000       # 最大速度 (步/秒)
    acceleration: 1000     # 加速度 (步/秒²)
  y_axis:
    steps_per_mm: 40     # Y 轴步数/毫米
    max_speed: 2000
    acceleration: 1000

# 剔除参数 (电磁阀/继电器)
ejection:
  blast_pin: 9            # 继电器控制引脚 (Arduino 数字引脚)
  blast_duration: 200     # 默认喷气时长 (毫秒)
```

---

## 🎯 配置优先级

```
1. 代码中的硬编码 (不推荐)
2. YAML 配置文件 (✅ 推荐)
```

**推荐做法**：所有参数都放在 YAML 文件中，代码里只写默认值。

---

## 🛠️ 高级用法

### 重新加载配置（热更新）
```python
from config.config import load_config

load_config()  # 重新从 YAML 文件加载配置
```

### 修改配置并保存

```python
from config.config import get_config, load_config

cfg = get_config()
cfg['serial']['port'] = 'COM4'   # 仅修改内存中的配置（重启/重载后失效）
# 持久化请直接编辑 device_params.yaml 中的 serial.port
load_config()                    # 重新从 YAML 加载（会覆盖上述内存修改）

```

---

## ⚠️ 注意事项

### 1. 修改配置后需要重启
应用启动时读取配置，运行时修改 YAML 文件不会自动生效。
需要调用 `load_config()` 或重启应用。

### 2. 串口端口需要根据实际修改
- **Windows**: `COM3`, `COM4`, ...
- **Linux**: `/dev/ttyUSB0`, `/dev/ttyACM0`, ...

查看设备管理器确认端口。

### 3. YAML 格式敏感
- 使用**空格**缩进（不要用 Tab）
- 冒号后要有**空格**（`key: value` ✅，`key:value` ❌）
- 列表用 `- ` 开头（横杠+空格）

---

## 🎓 学习要点

### 1. 配置外置原则
**错误做法**：
```python
# ❌ 硬编码在代码里
MODE = 'sim'
BAUD_RATE = 115200
```

**正确做法**：
```yaml
# ✅ 放在 YAML 文件里
# config/app_settings.yaml
mode: sim

# config/device_params.yaml
serial:
  baudrate: 115200
```

**好处**：
- 修改配置不用改代码
- 不同环境用不同配置文件
- 便于版本控制（敏感信息用 `.gitignore` 排除）

---

### 2. 配置分层原则
- **应用配置** (`app_settings.yaml`)：业务逻辑相关，所有环境通用
- **设备参数** (`device_params.yaml`)：硬件相关，不同设备不同

---

### 3. 简单直接的配置访问
**之前**（过度设计）：
```python
# ❌ 导出20+个全局变量
from config import MODE, PIXELS_PER_MM, ARDUINO_CONFIG, ...

if MODE == 'real':
    port = ARDUINO_CONFIG['port']
```

**之后**（简单直接）：
```python
# ✅ 用一个函数获取配置字典
from config import get_config

cfg = get_config()
if cfg['mode'] == 'real':
    port = cfg['serial']['port']
```

**好处**：
- 代码量少
- 清晰易读
- 易于维护

---

## 📖 相关文档
- `../README.md` - 项目总览
- `src/devices/README.md` - 设备层
- `src/core/README.md` - 业务逻辑层
- `src/ui/README.md` - UI 层

---

## 📝 版本历史
- **2026-07-17**: 新增 comm/writer/preview_fps/detect_fps/median_ksize 字段；仿真参数拆分子结构
- **2026-06-21**: 简化配置系统，删除过度设计
- **2026-06-21**: 合并 `configs/` 到 `config/`，统一配置目录
- **2025-10-09**: 初始版本
