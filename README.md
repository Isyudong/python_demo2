# 黄鳝鱼卵剔除系统

## 📋 项目简介
基于计算机视觉和 Arduino 控制的工控项目，用于自动检测和剔除不合格的黄鳝鱼卵。

**核心功能**：
1. 使用工业相机采集鱼卵图像
2. 通过霍夫圆变换检测圆形物体
3. 通过 HSV 颜色过滤区分良品（黄色）和次品（非黄色）
4. 控制两轴步进电机移动到目标位置
5. 触发电磁阀（高速气流）吹走次品

## 🏗️ 项目架构（多线程异步 + 4 层隔离）

```
┌─────────────────────────────────────────┐
│  UI 层 (src/ui/)                        │  ← PySide6 主线程
├─────────────────────────────────────────┤
│  业务逻辑层 (src/core/)                   │  ← Workflow + 消息契约(messages)
├─────────────────────────────────────────┤
│  设备层 (src/devices/)                   │  ← Sim/Real 双轨实现
├─────────────────────────────────────────┤
│  第三方库 (libs/vendor_libs/)            │  ← MVSDK (相机 SDK)
└─────────────────────────────────────────┘
         ↕ 串口通信 (Serial)
┌─────────────────────────────────────────┐
│  下位机 固件 (Arduino/)                  │  ← 电机控制 + 电磁阀控制
└─────────────────────────────────────────┘

线程模型：UI主线程 + 相机线程(常驻推流) + 通信线程(常驻协议序列) + 检测Worker(一次性) + Writer线程(常驻异步写盘)
上下位机协议：BATCH_START / TARGET / BATCH_COMPLETE / ABORT
```

**设计原则**：
- **简单直接**：能用一个变量解决的，不创建一个类
- **按需设计**：先满足需求，再考虑扩展
- **仿真/真实双模式**：SimArduino 模拟完整协议应答，开发时无需硬件
- **配置外置**：所有参数放在 `config/` 目录的 YAML 文件中
- **信号驱动**：线程间通过消息队列通信，无轮询阻塞

---

## 📁 目录结构

```
python_demo2-master/
├── config/               # 配置文件 + 配置加载器
│   ├── app_settings.yaml  # 应用配置（含 comm/writer/preview_fps 等）
│   ├── device_params.yaml # 设备参数
│   ├── config.py          # 配置加载器（读取 YAML，导出函数）
│   └── __init__.py       # 配置包导出
├── src/                  # 源代码
│   ├── devices/            # 设备层
│   │   ├── interfaces.py   # DeviceState 枚举 + 基类
│   │   ├── sim_impl.py     # 仿真实现（含完整协议应答）
│   │   ├── real_impl.py    # 真实硬件实现（send_raw timeout + send_with_retry）
│   │   └── factory.py      # 设备工厂
│   ├── core/               # 业务逻辑层
│   │   ├── messages.py     # 跨线程数据契约（FrameMessage/DetectionResult/CommStatus/CommRequest/WriterTask）
│   │   ├── workflow.py     # 工作流程管理器
│   │   ├── algorithm/      # 算法模块
│   │   └── utils/          # 工具类（坐标转换、ROI 管理）
│   └── ui/                 # UI 层
│       └── app_window.py   # 主窗口
├── libs/                 # 第三方库
│   └── vendor_libs/       # Vendor SDK
├── archive/              # 原始快照（不动）
├── data/                 # 数据文件
├── test_images/          # 测试图像（仿真模式用）
├── tools/                # 辅助工具脚本
├── tests/                # 测试用例
├── main.py               # 启动入口
├── pyproject.toml        # 项目包配置（可 pip install -e .）
└── requirements.txt      # Python 依赖
```

---

## 🚀 快速开始

### 1. 安装依赖
```bash
D:\Miniconda Settings\envs\imageprocessing\python.exe -m pip install -r requirements.txt
```

### 2. 运行仿真模式（无硬件）
```bash
D:\Miniconda Settings\envs\imageprocessing\python.exe main.py --sim
```

### 3. 运行真实模式（需要硬件）
```bash
D:\Miniconda Settings\envs\imageprocessing\python.exe main.py --real
```

---

## 📚 学习路径

### 第一阶段：理解架构
1. 阅读 `config/README.md` - 了解配置系统
2. 阅读 `src/devices/README.md` - 了解设备层（Sim/Real 双轨）
3. 阅读 `src/core/README.md` - 了解业务逻辑层（含 messages.py 数据契约）
4. 阅读 `src/ui/README.md` - 了解 UI 层

### 第二阶段：动手实践
1. 修改 `config/app_settings.yaml`，调整检测参数
2. 运行仿真模式，观察 UI 和日志
3. 修改 `src/core/algorithm/circle_detector.py`，尝试不同的检测方法

### 第三阶段：硬件集成
1. 上传 Arduino 固件到 Arduino 板
2. 连接相机和 Arduino
3. 运行真实模式，测试完整流程

---

## ⚙️ 配置文件说明

### app_settings.yaml
应用配置（业务逻辑相关）：
- `mode`: 运行模式（sim/real）
- `pixel_per_mm`: 像素到毫米比例
- `detection`: 圆形检测参数（含 median_ksize）
- `hsv_filter`: HSV 颜色过滤范围
- `preview_fps` / `detect_fps`: 帧率限制
- `comm`: 通信参数（timeout/retries/heartbeat_interval）
- `writer`: 写盘参数（max_queue）
- `simulation`: 仿真参数（含 camera/arduino 子配置）

### device_params.yaml
设备参数（硬件相关）：
- `serial`: 串口参数
- `camera`: 相机参数
- `motor`: 电机参数
- `ejection`: 剔除参数（电磁阀）

---

## 🔧 常见问题

### Q1: 仿真模式无法启动？
**A**: 检查 `PySide6` 是否安装：
```bash
D:\Miniconda Settings\envs\imageprocessing\python.exe -c "import PySide6"
```

### Q2: 真实模式找不到相机？
**A**: 检查 MVSDK 驱动是否安装，相机是否连接。

### Q3: Arduino 无法连接？
**A**: 检查 `config/device_params.yaml` 中的 `serial.port` 是否正确（例如 `COM3`）。

### Q4: 检测不到圆形？
**A**: 调整 `config/app_settings.yaml` 中的 `detection` 参数：
- 增大 `max_radius`
- 减小 `min_dist`
- 调整 `param1` 和 `param2`

---

## 📖 详细文档
每个目录下都有 `README.md` 文件，详细介绍该目录的功能和使用方法。

---

## 🎓 工业控制项目经验总结
通过这个项目，你可以学到：
1. **多线程异步架构**：UI主线程 + 相机推流 + 通信序列 + 检测Worker + 写盘
2. **Sim/Real 双轨设计**：仿真模拟完整协议应答，开发时无需硬件
3. **配置外置**：将参数放在 YAML 文件中，热加载支持
4. **PySide6 UI 开发**：信号与槽机制、回调函数
5. **串口通信协议设计**：请求-应答模式 + 超时重试
6. **计算机视觉**：霍夫圆变换 + HSV 颜色过滤

**代码精简原则**（2026-07-17 更新）：
- 删除过度抽象（如不必要的接口类）
- 删除数据包装类（直接返回原始数据）
- 简化工厂模式（用 if/else 代替复杂工厂）
- 保持代码简单、直接、易读
- 去AI化命名：模块用小写复数名词，忌 `_impl`/`_manager` 后缀

---

## 📝 版本历史
- **2026-07-17**: 多线程重构启动（Phase 0 完成）；SimArduino 新增协议应答；RealArduino 新增 send_with_retry；新增 messages.py 跨线程数据契约；config 新增 comm/writer/preview_fps/detect_fps/median_ksize 字段
- **2026-07-16**: 去AI化命名重构（factory/sim_impl/real_impl/coords/calib 等）；新增 DeviceBase 基类、DeviceState 枚举；添加 pyproject.toml
- **2026-06-21**: 精简代码，删除过度设计，更新文档
- **2026-06-21**: 重构项目，应用 4 层隔离架构
- **2025-10-09**: 初始版本

---

## 📞 联系方式
如有问题，请提交 Issue 或联系开发者。
