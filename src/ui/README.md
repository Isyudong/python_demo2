# src/ui/ - 用户界面层

## 📋 目录说明
存放用户界面相关的代码，使用 PySide6 构建。

## 📁 文件列表

### __init__.py
Python 包初始化文件。

### app_window.py
**主窗口类** - 应用程序的主界面，使用 PySide6 构建。

## 🔧 主要功能

### MainWindow 类 (`app_window.py`)
主窗口界面，提供：
1. **模式切换**：简单模式 / 专家模式
2. **相机控制**：启动/停止相机，单张采集，连续采集
3. **检测控制**：运行检测，查看结果
4. **运动控制**：手动微调位置（jog 控制）
5. **参数设置**：调整检测参数、相机参数、Arduino 参数
6. **日志显示**：显示系统日志和状态信息
7. **实时预览**：显示相机实时画面

## 📝 代码示例

### 启动 UI
```python
import sys
from PySide6.QtWidgets import QApplication
from src.ui.app_window import MainWindow

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
```

### 通过命令行启动
```bash
python main.py --sim    # 仿真模式
python main.py --real   # 真实模式
```

## 🎨 UI 布局

### 简单模式
- 相机控制按钮
- 检测控制按钮
- 状态显示
- 实时预览

### 专家模式
- 检测参数调整（霍夫圆变换参数）
- 颜色过滤调整（HSV 范围）
- 相机参数调整（曝光时间）
- Arduino 参数调整（串口配置、喷气时长）
- 校准工具
- 日志查看器

## ⚠️ 注意事项
- UI 层通过 `Workflow` 类与业务逻辑交互，不直接操作设备
- 修改 UI 后需要重启程序
- 仿真模式下不需要真实硬件，适合开发和学习

## 🎓 学习要点
- **MVC 模式**：Model（`Workflow`）= 业务逻辑，View（`MainWindow`）= 界面，Controller = 回调函数
- **信号与槽**：PySide6 的核心机制，用于组件间通信
- **线程安全**：UI 更新必须在主线程，耗时操作通过消息队列异步执行
- **响应式设计**：界面应能适应不同分辨率和 DPI

## 📝 版本历史
- **2026-07-17**: 更新线程模型说明（新增相机线程/通信线程/检测Worker/Writer线程）
- **2026-06-21**: 从 `userTest/` 移入并整理
- **2025-10-09**: 初始版本
