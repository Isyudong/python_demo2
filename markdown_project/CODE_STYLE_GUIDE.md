# 代码风格指南

## 概述

本文档定义了视觉检测系统项目的代码风格规范，确保代码的一致性和可维护性。

## 1. 通用规范

### 1.1 编码规范
- 使用 UTF-8 编码
- 遵循 PEP 8 规范
- 使用 4 个空格进行缩进，不使用 Tab

### 1.2 命名规范
- **类名**: 使用 PascalCase（如：`VisionSystem`）
- **函数/方法名**: 使用 snake_case（如：`process_frame`）
- **变量名**: 使用 snake_case（如：`is_initialized`）
- **常量名**: 使用 UPPER_SNAKE_CASE（如：`WINDOW_NAMES`）
- **私有方法**: 使用下划线前缀（如：`_load_config`）

### 1.3 文件命名
- 模块文件使用 snake_case（如：`vision_system.py`）
- 包目录使用小写字母（如：`camera/`, `utils/`）

## 2. 代码组织

### 2.1 导入顺序
```python
# 1. 标准库导入
import os
import sys
import time

# 2. 第三方库导入
import cv2
import numpy as np

# 3. 本地模块导入
from .constants import WINDOW_NAMES
from .utils.roi_manager import ROIManager
```

### 2.2 类结构
```python
class ExampleClass:
    """类的文档字符串"""
    
    def __init__(self):
        """构造函数"""
        # 公共属性
        self.public_attr = None
        # 私有属性
        self._private_attr = None
    
    def public_method(self):
        """公共方法"""
        pass
    
    def _private_method(self):
        """私有方法"""
        pass
```

## 3. 文档字符串规范

### 3.1 模块文档字符串
```python
"""
模块简要描述
详细描述模块功能和用途
"""
```

### 3.2 类文档字符串
```python
class VisionSystem:
    """
    视觉系统主类
    
    负责整合所有功能模块，提供统一的应用接口。
    支持相机控制、图像处理、目标检测和串口通信。
    
    Attributes:
        is_initialized (bool): 系统是否已初始化
        is_running (bool): 系统是否正在运行
    """
```

### 3.3 方法文档字符串
```python
def process_frame(self, frame: np.ndarray, store_results: bool = False) -> Tuple[np.ndarray, List[Dict]]:
    """
    处理单帧图像并检测目标
    
    Args:
        frame (np.ndarray): 输入图像帧
        store_results (bool): 是否储存检测结果，默认为 False
        
    Returns:
        Tuple[np.ndarray, List[Dict]]: 包含处理后图像和检测结果的元组
        
    Raises:
        ValueError: 当输入图像格式无效时
        RuntimeError: 当系统未初始化时
        
    Example:
        >>> processed_frame, detections = vision_system.process_frame(frame, True)
        >>> print(f"检测到 {len(detections)} 个目标")
    """
```

## 4. 类型注解规范

### 4.1 基本类型注解
```python
from typing import Optional, Dict, List, Tuple, Union, Any

# 函数参数和返回值
def load_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    pass

# 变量注解
camera_info: Dict[str, Union[int, str, bool]] = {}
detection_results: List[Tuple[float, float, float]] = []
```

### 4.2 复杂类型注解
```python
from typing import TypedDict, Protocol

# 定义结构化类型
class DetectionResult(TypedDict):
    roi_index: int
    x_mm: float
    y_mm: float
    radius_mm: float
    is_valid: bool

# 协议定义
class Drawable(Protocol):
    def draw(self, frame: np.ndarray) -> None: ...
```

## 5. 错误处理规范

### 5.1 异常类定义
```python
class VisionSystemError(Exception):
    """视觉系统基础异常类"""
    pass

class CameraError(VisionSystemError):
    """相机相关异常"""
    pass
```

### 5.2 异常处理模式
```python
try:
    # 可能出错的代码
    result = risky_operation()
except SpecificError as e:
    # 处理特定异常
    logger.error(f"特定错误: {e}")
    raise
except Exception as e:
    # 处理通用异常
    logger.error(f"未预期的错误: {e}")
    # 可选：转换为自定义异常
    raise VisionSystemError(f"操作失败: {e}") from e
finally:
    # 清理资源
    cleanup_resources()
```

## 6. 常量和配置规范

### 6.1 常量定义
```python
# 在 constants.py 中定义
WINDOW_NAMES = {
    'REALTIME': "Real-time Picture",
    'PROCESSING': "Processing Picture"
}

# 使用常量
cv2.namedWindow(WINDOW_NAMES['REALTIME'], cv2.WINDOW_NORMAL)
```

### 6.2 配置管理
```python
# 配置应该是可配置的，不硬编码
DEFAULT_CONFIG = {
    'CAMERA_CONFIG': {
        'exposure_time': 30000,
        'target_resolution': None
    }
}
```

## 7. 日志规范

### 7.1 日志级别使用
```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: 详细的调试信息
logger.debug("处理第 %d 帧图像", frame_count)

# INFO: 一般信息
logger.info("系统初始化完成")

# WARNING: 警告信息
logger.warning("Arduino连接失败，将无法发送数据")

# ERROR: 错误信息
logger.error("相机初始化失败: %s", error_message)

# CRITICAL: 严重错误
logger.critical("系统崩溃: %s", critical_error)
```

## 8. 测试规范

### 8.1 测试文件命名
- 测试文件以 `test_` 开头
- 测试类以 `Test` 开头
- 测试方法以 `test_` 开头

```python
# test_vision_system.py
class TestVisionSystem:
    def test_initialization(self):
        """测试系统初始化"""
        pass
    
    def test_process_frame(self):
        """测试图像处理"""
        pass
```

### 8.2 断言使用
```python
import pytest

def test_detection_result():
    result = process_frame(test_frame)
    
    # 使用描述性的断言消息
    assert len(result) > 0, "应该检测到至少一个目标"
    assert result[0]['x_mm'] > 0, "X坐标应该为正数"
```

## 9. 性能优化规范

### 9.1 避免过早优化
- 首先保证代码正确性
- 使用性能分析工具识别瓶颈
- 只优化真正的性能瓶颈

### 9.2 资源管理
```python
# 使用上下文管理器
with VisionSystem() as vision_system:
    vision_system.run_detection()
# 自动清理资源

# 手动资源管理
try:
    vision_system = VisionSystem()
    vision_system.initialize()
    # 使用系统
finally:
    vision_system.cleanup()
```

## 10. 版本控制规范

### 10.1 提交消息格式
```
类型(范围): 简短描述

详细描述（可选）

相关问题编号（可选）
```

示例：
```
feat(camera): 添加自动曝光控制功能

实现了基于场景亮度的自动曝光调节算法，
提高了不同光照条件下的图像质量。

Closes #123
```

### 10.2 分支命名
- `feature/功能名称`: 新功能开发
- `bugfix/问题描述`: Bug 修复
- `hotfix/紧急修复`: 紧急修复
- `refactor/重构内容`: 代码重构

## 11. 代码审查检查清单

### 11.1 功能性检查
- [ ] 代码逻辑正确
- [ ] 处理了所有边界情况
- [ ] 错误处理完善
- [ ] 性能可接受

### 11.2 代码质量检查
- [ ] 遵循命名规范
- [ ] 文档字符串完整
- [ ] 类型注解正确
- [ ] 没有代码重复

### 11.3 安全性检查
- [ ] 输入验证充分
- [ ] 没有硬编码敏感信息
- [ ] 资源正确释放
- [ ] 异常处理安全

## 12. 工具推荐

### 12.1 代码格式化
- `black`: 自动代码格式化
- `isort`: 导入语句排序

### 12.2 代码检查
- `flake8`: 代码风格检查
- `mypy`: 类型检查
- `pylint`: 综合代码质量检查

### 12.3 测试工具
- `pytest`: 测试框架
- `coverage.py`: 测试覆盖率
- `pytest-mock`: 模拟测试

---

遵循这些规范可以确保代码库的一致性、可维护性和可读性。所有团队成员都应该熟悉并遵循这些规范。
