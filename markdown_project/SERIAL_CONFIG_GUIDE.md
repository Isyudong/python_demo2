# 统一串口配置管理说明

## 📋 配置文件位置
所有串口配置统一管理在：`config/config.py`

## 🔧 快速配置Arduino串口

### 方法1：自动检测配置（推荐）
```bash
python setup_arduino_port.py
```
此工具会：
- 自动检测系统中的所有串口设备
- 测试Arduino通信
- 自动更新配置文件

### 方法2：手动修改配置文件
编辑 `config/config.py` 文件：
```python
ARDUINO_CONFIG = {
    'port': '/dev/ttyUSB0',     # 修改为您的Arduino串口
    'baudrate': 115200,         # 波特率（通常不需要修改）
    'timeout': 15,              # 超时时间（秒）
    # ... 其他配置
}
```

## 🔍 常见Arduino串口
- **USB转串口**: `/dev/ttyUSB0`, `/dev/ttyUSB1`
- **原生USB**: `/dev/ttyACM0`, `/dev/ttyACM1`
- **传统串口**: `/dev/ttyS0`, `/dev/ttyS1`

## 📝 配置统一的好处

### 之前的问题
- 多个文件中有不同的串口配置
- 修改串口需要改多个地方
- 容易出现配置不一致

### 现在的解决方案
- ✅ 所有串口配置集中在 `config/config.py`
- ✅ 所有模块自动从配置文件读取
- ✅ 一处修改，全局生效
- ✅ 支持参数覆盖（代码中仍可传入特定参数）

## 🚀 使用方法

### 1. 首次配置
```bash
# 自动检测并配置Arduino串口
python setup_arduino_port.py
```

### 2. 验证配置
```bash
# 测试串口配置是否正确
python basic_test.py
```

### 3. 运行完整系统
```bash
# 运行视觉检测系统
python main.py
```

## 📊 配置文件结构

```python
config/config.py:
├── ARDUINO_CONFIG          # Arduino串口配置
├── BATCH_PROCESSING_CONFIG # 批量处理配置  
├── CAMERA_CONFIG          # 相机配置
├── CIRCLE_DETECTION_PARAMS # 检测参数配置
└── DISPLAY_CONFIG         # 显示配置
```

## 🔧 高级配置

如果需要在代码中使用特定的串口设置，仍然可以传入参数：
```python
# 使用配置文件设置
comm = CommunicationAdapter()

# 或者覆盖特定参数
comm = CommunicationAdapter(port='/dev/ttyUSB1', timeout=20)
```

## ⚠️ 注意事项

1. **权限问题**: 确保当前用户有串口访问权限
   ```bash
   sudo usermod -a -G dialout $USER
   # 注销重新登录后生效
   ```

2. **串口占用**: 确保串口没有被其他程序占用
   ```bash
   # 查看串口使用情况
   lsof /dev/ttyUSB0
   ```

3. **Arduino状态**: 确保Arduino已正确烧录代码并运行正常

现在您只需要在一个地方修改串口配置，整个系统都会使用新的设置！
