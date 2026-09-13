# src/devices/ - 设备层

## 📋 目录说明
存放设备的具体实现类和设备工厂，实现**硬件无关**的设计。

**设计理念**（精简后）：
- **简单直接**：直接用具体类，不创建不必要的抽象接口
- **方法签名一致**：仿真类和真实类的方法名、参数、返回值保持一致
- **按需扩展**：等真的需要切换设备时，再添加接口抽象也不迟

---

## 📁 文件列表

### interfaces.py
**设备基类 + 状态枚举**
- `DeviceState`: 枚举（IDLE/BUSY/ALARM/DISCONNECTED）
- `DeviceBase`: 设备基类（提供 `_log()` / `set_message_callback()` 公用能力）

### sim_impl.py
**仿真实现** - 无硬件时的模拟设备
- `SimCamera`: 仿真相机（从 `test_images/` 读取图片）
- `SimArduino`: 仿真 Arduino（完整协议应答：BATCH_START/TARGET/BATCH_COMPLETE/ABORT）

### real_impl.py
**真实硬件实现** - 包装真实硬件
- `RealCamera`: 真实相机（调用 MVSDK）
- `RealArduino`: 真实 Arduino（`send_raw` 支持 timeout 参数 + `send_with_retry` 超时重试）

### factory.py
**设备工厂** - 根据模式创建设备实例（简化版，用 if/else）
- `create_camera()`: 创建相机（sim 或 real）
- `create_arduino()`: 创建 Arduino（sim 或 real）
- `set_mode()`: 设置模式

---

## 🔧 使用方法

### 1. 通过工厂创建设备（✅ 推荐）
```python
from src.devices import create_camera, create_arduino, get_mode

# 根据配置创建设备
camera = create_camera()
arduino = create_arduino()

print(f"当前模式: {get_mode().upper()}")
print(f"相机类型: {type(camera).__name__}")
```

**好处**：简单直接，一行代码创建设备。

---

### 2. 直接使用设备类
```python
# 仿真模式
from src.devices.sim_impl import SimCamera, SimArduino

camera = SimCamera()
arduino = SimArduino()

# 真实模式
from src.devices.real_impl import RealCamera, RealArduino

camera = RealCamera()
arduino = RealArduino()
```

**场景**：需要自定义设备参数时。

---

### 3. 切换仿真/真实模式
**方式 1**：修改 `config/app_settings.yaml`
```yaml
mode: sim    # 或 real
```

**方式 2**：命令行参数
```bash
python main.py --sim    # 使用仿真设备
python main.py --real   # 使用真实设备
```

**方式 3**：运行时切换（仅影响后续创建的设备）
```python
from src.devices import set_mode

set_mode('real')  # 切换到真实模式
```

---

## 📝 代码示例

### 使用仿真相机
```python
from src.devices.sim_impl import SimCamera

camera = SimCamera()
camera.connect()

# 采集一帧（直接返回 numpy 数组，无需包装成对象）
frame = camera.grab_frame()
if frame is not None:
    print(f"仿真图像形状: {frame.shape}")

camera.disconnect()
```

---

### 使用真实相机
```python
from src.devices.real_impl import RealCamera

camera = RealCamera()
camera.connect()

# 采集一帧（直接返回 numpy 数组）
frame = camera.grab_frame()
if frame is not None:
    print(f"真实图像形状: {frame.shape}")

camera.disconnect()
```

---

### 使用仿真 Arduino
```python
from src.devices.sim_impl import SimArduino

arduino = SimArduino()
arduino.connect()

# 移动电机
arduino.move_absolute(x=10.0, y=20.0)

# 触发电磁阀
arduino.blast_on(duration_ms=200)
arduino.blast_off()

# 查询位置（返回字典，而非对象）
pos = arduino.get_position()
print(f"X={pos['x']}, Y={pos['y']}")

arduino.disconnect()
```

---

## ⚠️ 注意事项

### 1. 仿真模式和真实模式的方法签名一致
虽然删除了接口抽象，但仿真类和真实类的方法名、参数、返回值保持一致：
```python
# SimCamera 和 RealCamera 都有这些方法
camera.connect()           # → bool
camera.disconnect()        # → None
camera.grab_frame()        # → Optional[np.ndarray]
camera.get_state()         # → str
```

**好处**：切换模式时，业务逻辑代码无需修改。

---

### 2. 直接返回原始数据（无包装类）
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

### 3. 仿真实现可以用于自动化测试
```python
def test_detection():
    """使用仿真相机测试检测算法"""
    camera = SimCamera()
    camera.connect()
    
    frame = camera.grab_frame()
    # 测试检测算法...
```

---

## 🎓 学习要点

### 1. 简单直接原则
**问题代码**（过度设计）：
```python
# ❌ 创建一个接口筷子，只是为了夹起一个实现叉子
class ICamera(ABC):
    @abstractmethod
    def grab_frame(self) -> Optional[CameraFrame]: ...

class SimCamera(ICamera):
    def grab_frame(self) -> Optional[CameraFrame]:
        return CameraFrame(image=frame, timestamp=time.time())

# 使用时还要解包
img = frame_obj.image
```

**精简后代码**（简单直接）：
```python
# ✅ 直接用具体类，直接返回数据
class SimCamera:
    def grab_frame(self) -> Optional[np.ndarray]:
        return frame.copy()

# 直接使用
img = frame
```

**好处**：
- 代码量少 30-40%
- 清晰易读
- 易于调试

---

### 2. 按需设计原则
**错误做法**：
- 为"可能的未来需求"提前创建抽象层
- 项目只有一个相机，却定义了 `ICamera` 接口
- 项目只有一个控制器，却定义了 `IArduino` 接口

**正确做法**：
- 先满足当前需求，再考虑扩展
- 等到真的需要切换设备时，再添加接口抽象也不迟
- 保持代码简单、直接、易读

---

### 3. 方法签名一致
虽然删除了接口抽象，但保持仿真类和真实类的方法签名一致：
```python
# SimCamera 和 RealCamera 的方法签名一致
def grab_frame(self) -> Optional[np.ndarray]: ...
```

**好处**：
- 切换模式时，业务逻辑代码无需修改
- 如果未来真的需要接口抽象，可以轻松添加

---

## 📖 相关文档
- `../README.md` - 项目总览
- `../../config/README.md` - 配置系统
- `../core/README.md` - 业务逻辑层
- `../ui/README.md` - UI 层

---

## 📝 版本历史
- **2026-07-17**: SimArduino 新增协议应答（BATCH_START/TARGET/BATCH_COMPLETE/ABORT）；RealArduino 新增 send_with_retry；新增 DeviceBase 基类、DeviceState 枚举
- **2026-06-21**: 删除接口抽象，简化设备层
- **2026-06-21**: 重构项目，应用 4 层隔离架构
- **2025-10-09**: 初始版本
