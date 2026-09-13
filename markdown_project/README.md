# markdown_project/ - 项目文档

## 📋 目录说明
存放项目的 Markdown 文档（设计文档、开发指南、串口配置等）。

## 📄 文件列表

| 文件 | 说明 |
|------|------|
| `ARDUINO_COMPATIBILITY.md` | Arduino 兼容性说明（G-code 协议、命令格式） |
| `CODE_STYLE_GUIDE.md` | Python 代码风格指南（PEP 8、命名规范） |
| `README_COORDINATE_CONVERSION.md` | 坐标转换说明（像素坐标 → 电机坐标） |
| `SERIAL_CONFIG_GUIDE.md` | 串口配置指南（Arduino 串口通信配置） |

## 📝 文档摘要

### ARDUINO_COMPATIBILITY.md
**主要内容**：
- Arduino 支持的 G-code 命令（`G0`, `G1`, `?`, `STOP`, `RESET`）
- 手动调试命令（`O`, `V`, `M`, `R`, `S`, `A`, `X`, `D`, `B`, `H`）
- 电磁阀控制命令（`BLAST ON`, `BLAST OFF`）

**使用场景**：
- 理解 Arduino 固件的命令格式
- 调试串口通信问题
- 添加新命令

---

### CODE_STYLE_GUIDE.md
**主要内容**：
- Python 代码风格（PEP 8）
- 命名规范（变量、函数、类、常量）
- 注释规范（行注释、文档字符串）
- 项目特定规范（配置文件、日志格式）

**使用场景**：
- 新成员了解代码风格
- 提交代码前自查
- Code Review 标准

---

### README_COORDINATE_CONVERSION.md
**主要内容**：
- 坐标转换原理（像素坐标 → 世界坐标）
- `CoordinateConverter` 类使用方法
- 校准流程（计算 `pixel_per_mm`）

**使用场景**：
- 理解坐标转换算法
- 调试坐标偏差问题
- 重新校准系统

---

### SERIAL_CONFIG_GUIDE.md
**主要内容**：
- 串口参数说明（波特率、超时、重试）
- Arduino 串口初始化流程
- 常见问题排查

**使用场景**：
- 配置串口连接
- 调试串口通信问题
- 理解 `ARDUINO_CONFIG` 配置项

---

## 🔧 使用方法

### 查看文档
用任意 Markdown 编辑器打开，推荐：
- **VS Code** + Markdown Preview 插件
- **Typora**（实时预览）
- **Obsidian**（知识库管理）

### 更新文档
如果设计有变更，同步更新对应文档：
1. 修改 Markdown 文件
2. 提交到 git（`git add . && git commit -m "更新文档"`）

---

## ⚠️ 注意事项

### 1. 文档与代码同步
代码变更时，同步更新相关文档（防止文档过时）。

### 2. 文档命名规范
- 使用大写字母+下划线（如 `CODE_STYLE_GUIDE.md`）
- 文件名要能清楚表达内容

### 3. 文档格式
- 使用 Markdown 格式（`.md` 后缀）
- 包含目录（长文档）
- 包含代码示例（如果适用）

---

## 🎓 学习要点

### 1. 文档驱动开发
好的文档能：
- 降低新成员上手成本
- 减少重复回答相同问题
- 提高代码可维护性

### 2. 文档类型
- **设计文档**：记录架构决策（为什么这样设计？）
- **使用指南**：教用户如何使用（怎么用？）
- **开发指南**：教开发者如何贡献（如何改？）

### 3. Markdown 技巧
- **标题层级**：`#` → 一级标题，`##` → 二级标题
- **代码块**：用 ```python ... ``` 包裹代码
- **表格**：用 `|` 分隔单元格
- **链接**：用 `[文字](URL)` 插入链接

---

## 📖 相关文档
- `README.md` - 项目总览
- `config/README.md` - 配置说明
- `src/devices/README.md` - 设备抽象层
- `src/core/README.md` - 业务逻辑层
- `src/ui/README.md` - UI 层

---

## 📝 版本历史
- **2026-07-17**: 更新串口配置引用路径，反映当前项目结构
- **2026-06-21**: 从 `Makdown_Project/` 重命名（修正拼写）
- **2025-10-09**: 初始版本
