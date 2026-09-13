# data/ - 数据文件

## 📋 目录说明
存放项目运行所需的数据文件。

## 📁 文件列表

### roi.txt
**ROI（感兴趣区域）配置文件** - 定义图像中需要处理的区域
- 格式：`x, y, width, height`
- 用途：减少处理区域，提高性能
- 状态：当前版本未使用，保留供未来使用

## 🔧 使用方法

### 读取 ROI 配置
```python
from src.core.utils.roi_manager import ROIManager

roi_manager = ROIManager('data/roi.txt')
rois = roi_manager.load_rois()
print(f"加载了 {len(rois)} 个 ROI")
```

### 保存 ROI 配置
```python
rois = [(100, 100, 200, 200), (300, 300, 150, 150)]
roi_manager.save_rois(rois)
```

## ⚠️ 注意事项
- ROI 坐标是基于原始图像分辨率的
- 如果修改了相机分辨率，需要重新校准 ROI
- 当前版本使用全图检测，ROI 功能暂未启用

## 🎓 学习要点
- **ROI 优化**：通过限定处理区域提高性能
- **配置文件管理**：将数据与代码分离
- **未来扩展**：保留接口，便于后续启用

## 📝 版本历史
- **2026-07-17**: 更新 README，明确当前状态
- **2026-06-21**: 随项目重构移入
- **2025-10-09**: 初始版本
