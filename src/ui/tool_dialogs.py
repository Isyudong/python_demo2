"""
工具对话框 — 从主界面「工具」菜单打开。

每个对话框封装 tools/ 下的一个脚本功能，避免用户在终端中手动运行。
"""

import sys
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QFileDialog, QGroupBox, QMessageBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt

# 项目根目录：本文件位于 src/ui/，向上两级即仓库根
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── 通用样式 ──────────────────────────────────────

_BTN_PRIMARY = "#3584e4"
_BTN_DESTRUCTIVE = "#e01b24"
_BTN_NEUTRAL = "#999999"
_BORDER = "#e0e0e0"
_BG = "#f6f5f4"


def _btn_style(color):
    return (
        f"QPushButton {{"
        f"  background-color: {color};"
        f"  color: white;"
        f"  border: none;"
        f"  border-radius: 6px;"
        f"  padding: 6px 16px;"
        f"  font-size: 13px;"
        f"}}"
        f"QPushButton:hover {{ background-color: {color}cc; }}"
        f"QPushButton:disabled {{ background-color: #ccc; }}"
    )


def _input_style():
    return (
        "QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {"
        "  border: 1px solid #d0d0d0;"
        "  border-radius: 4px;"
        "  padding: 4px 8px;"
        "  background-color: white;"
        "  color: #333;"
        "}"
        "QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {"
        "  border-color: #3584e4;"
        "}"
    )


def _dialog_stylesheet():
    return (
        f"QDialog {{ background-color: {_BG}; }}"
        f"QLabel {{ color: #333; }}"
        f"QGroupBox {{"
        f"  border: 1px solid {_BORDER};"
        f"  border-radius: 8px;"
        f"  margin-top: 12px;"
        f"  padding: 16px 8px 8px 8px;"
        f"  background-color: white;"
        f"}}"
        f"QGroupBox::title {{"
        f"  subcontrol-origin: margin;"
        f"  left: 12px;"
        f"  padding: 0 6px;"
        f"  color: #333;"
        f"}}"
        + _input_style()
    )


# ── 相机标定对话框 ────────────────────────────────

class CalibDialog(QDialog):
    """相机标定对话框：选择棋盘格图片目录 -> 设参数 -> 运行标定 -> 保存 pkl。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("相机标定")
        self.setMinimumWidth(480)
        self.setStyleSheet(_dialog_stylesheet())
        self._calibrator = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 图片目录
        dir_group = QGroupBox("标定图片目录")
        dir_layout = QHBoxLayout(dir_group)
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("选择包含棋盘格图片的目录...")
        dir_layout.addWidget(self.dir_edit)
        btn_browse = QPushButton("浏览")
        btn_browse.setStyleSheet(_btn_style(_BTN_NEUTRAL))
        btn_browse.clicked.connect(self._on_browse_dir)
        dir_layout.addWidget(btn_browse)
        layout.addWidget(dir_group)

        # 棋盘格参数
        param_group = QGroupBox("棋盘格参数")
        form = QFormLayout(param_group)
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(2, 30)
        self.cols_spin.setValue(10)
        form.addRow("内角点列数", self.cols_spin)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(2, 30)
        self.rows_spin.setValue(7)
        form.addRow("内角点行数", self.rows_spin)

        self.square_spin = QDoubleSpinBox()
        self.square_spin.setRange(1.0, 100.0)
        self.square_spin.setValue(18.0)
        self.square_spin.setSuffix(" mm")
        form.addRow("方格实际尺寸", self.square_spin)
        layout.addWidget(param_group)

        # 运行按钮
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("运行标定")
        self.btn_run.setStyleSheet(_btn_style(_BTN_PRIMARY))
        self.btn_run.clicked.connect(self._on_run)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run)
        layout.addLayout(btn_layout)

        # 结果输出
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(160)
        self.result_text.setStyleSheet(
            "background-color: #2d2d2d; color: #33d17a;"
            " border-radius: 6px; font-family: monospace; font-size: 12px;"
        )
        layout.addWidget(self.result_text)

    def _on_browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择标定图片目录")
        if d:
            self.dir_edit.setText(d)

    def _log(self, msg):
        self.result_text.append(msg)

    def _on_run(self):
        img_dir = self.dir_edit.text().strip()
        if not img_dir or not os.path.isdir(img_dir):
            QMessageBox.warning(self, "错误", "请选择有效的图片目录")
            return

        cols = self.cols_spin.value()
        rows = self.rows_spin.value()
        square = self.square_spin.value()

        self._log(f">>> 开始标定：{img_dir}")
        self._log(f"    棋盘内角点：{cols}x{rows}，方格尺寸：{square}mm")

        try:
            from calib import CameraCalibrator

            calibrator = CameraCalibrator(
                checkerboard_size=(cols, rows),
                square_size=square,
            )
            self._calibrator = calibrator

            if not calibrator.load_images_from_directory(img_dir):
                self._log("!!! 未找到有效棋盘格图片")
                return

            self._log(f">>> 成功处理 {len(calibrator.objpoints)} 张图片")

            if calibrator.calibrate_camera():
                err = calibrator.calibration_error
                self._log(f"<<< 标定成功！重投影误差：{err:.4f}")

                save_path = os.path.join(_PROJECT_ROOT, "camera_calibration.pkl")
                if calibrator.save_calibration(save_path):
                    self._log(f"<<< 标定结果已保存：{save_path}")
            else:
                self._log("!!! 标定失败")

        except Exception as e:
            self._log(f"!!! 异常：{e}")


# ── 像素比例计算对话框 ──────────────────────────────

class ScaleDialog(QDialog):
    """像素比例计算对话框：读 pkl -> 输入工作距离 -> 计算 pixel_per_mm -> 写回配置。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("像素比例计算")
        self.setMinimumWidth(440)
        self.setStyleSheet(_dialog_stylesheet())
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 标定文件
        file_group = QGroupBox("标定文件")
        file_layout = QHBoxLayout(file_group)
        self.pkl_edit = QLineEdit()
        self.pkl_edit.setPlaceholderText("camera_calibration.pkl")
        default_pkl = os.path.join(_PROJECT_ROOT, "camera_calibration.pkl")
        if os.path.exists(default_pkl):
            self.pkl_edit.setText(default_pkl)
        file_layout.addWidget(self.pkl_edit)
        btn_browse = QPushButton("浏览")
        btn_browse.setStyleSheet(_btn_style(_BTN_NEUTRAL))
        btn_browse.clicked.connect(self._on_browse_pkl)
        file_layout.addWidget(btn_browse)
        layout.addWidget(file_group)

        # 工作距离
        dist_group = QGroupBox("工作距离")
        dist_form = QFormLayout(dist_group)
        self.dist_spin = QDoubleSpinBox()
        self.dist_spin.setRange(10.0, 2000.0)
        self.dist_spin.setValue(300.0)
        self.dist_spin.setSuffix(" mm")
        dist_form.addRow("相机到被测物距离", self.dist_spin)
        layout.addWidget(dist_group)

        # 按钮
        btn_layout = QHBoxLayout()
        self.btn_calc = QPushButton("计算并保存")
        self.btn_calc.setStyleSheet(_btn_style(_BTN_PRIMARY))
        self.btn_calc.clicked.connect(self._on_calculate)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_calc)
        layout.addLayout(btn_layout)

        # 结果
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(140)
        self.result_text.setStyleSheet(
            "background-color: #2d2d2d; color: #33d17a;"
            " border-radius: 6px; font-family: monospace; font-size: 12px;"
        )
        layout.addWidget(self.result_text)

    def _on_browse_pkl(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择标定文件", "", "Pickle Files (*.pkl)"
        )
        if path:
            self.pkl_edit.setText(path)

    def _log(self, msg):
        self.result_text.append(msg)

    def _on_calculate(self):
        pkl_path = self.pkl_edit.text().strip()
        if not pkl_path or not os.path.isfile(pkl_path):
            QMessageBox.warning(self, "错误", "请选择有效的标定文件")
            return

        distance = self.dist_spin.value()

        self._log(f">>> 加载标定文件：{pkl_path}")
        try:
            from scale import PixelScale

            calc = PixelScale(calibration_file=pkl_path)
            if calc.camera_matrix is None:
                self._log("!!! 无法加载标定数据")
                return

            self._log(f">>> 工作距离：{distance}mm")
            result = calc.calculate_ratio_from_checkerboard(distance)

            if result:
                ratio = result['avg_ratio_pixels_per_mm']
                self._log(f"<<< pixel_per_mm = {ratio:.2f}")
                self._log("<<< 已写入 config/app_settings.yaml")
                QMessageBox.information(
                    self, "成功",
                    f"像素比例已计算并保存：\n{ratio:.2f} pixels/mm"
                )

        except Exception as e:
            self._log(f"!!! 异常：{e}")


# ── 串口测试对话框 ────────────────────────────────

class SerialTestDialog(QDialog):
    """串口测试对话框：选串口/波特率 -> 发送指令 -> 显示响应。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("串口测试")
        self.setMinimumWidth(460)
        self.setStyleSheet(_dialog_stylesheet())
        self._serial = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 连接参数
        conn_group = QGroupBox("连接参数")
        conn_form = QFormLayout(conn_group)

        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        for p in [
            "/dev/ttyUSB0", "/dev/ttyUSB1",
            "/dev/ttyACM0", "/dev/ttyACM1",
            "/dev/ttyS0", "/dev/ttyS1",
        ]:
            self.port_combo.addItem(p)
        conn_form.addRow("串口", self.port_combo)

        self.baud_combo = QComboBox()
        for b in ["9600", "19200", "38400", "57600", "115200"]:
            self.baud_combo.addItem(b)
        self.baud_combo.setCurrentText("115200")
        conn_form.addRow("波特率", self.baud_combo)
        layout.addWidget(conn_group)

        # 连接按钮
        btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("连接")
        self.btn_connect.setStyleSheet(_btn_style(_BTN_PRIMARY))
        self.btn_connect.setCheckable(True)
        self.btn_connect.clicked.connect(self._on_connect)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_connect)
        layout.addLayout(btn_layout)

        # 指令输入
        cmd_group = QGroupBox("发送指令")
        cmd_layout = QHBoxLayout(cmd_group)
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("输入指令，如: G0 X10 Y10")
        self.cmd_edit.returnPressed.connect(self._on_send)
        cmd_layout.addWidget(self.cmd_edit)
        self.btn_send = QPushButton("发送")
        self.btn_send.setStyleSheet(_btn_style(_BTN_PRIMARY))
        self.btn_send.clicked.connect(self._on_send)
        cmd_layout.addWidget(self.btn_send)
        layout.addWidget(cmd_group)

        # 快捷指令
        quick_layout = QHBoxLayout()
        for cmd_text in ["?", "v", "STOP", "RESET"]:
            btn = QPushButton(cmd_text)
            btn.setStyleSheet(_btn_style(_BTN_NEUTRAL))
            btn.clicked.connect(lambda _, c=cmd_text: self._send_quick(c))
            quick_layout.addWidget(btn)
        quick_layout.addStretch()
        layout.addLayout(quick_layout)

        # 响应显示
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setStyleSheet(
            "background-color: #2d2d2d; color: #33d17a;"
            " border-radius: 6px; font-family: monospace; font-size: 12px;"
        )
        layout.addWidget(self.response_text)

    def _log(self, msg):
        self.response_text.append(msg)

    def _on_connect(self):
        if self.btn_connect.isChecked():
            port = self.port_combo.currentText()
            baudrate = int(self.baud_combo.currentText())
            try:
                import serial # type: ignore
                self._serial = serial.Serial(port, baudrate, timeout=2)
                self._log(f"[INFO] 已连接 {port} @ {baudrate}")
                self.btn_connect.setText("断开")
                self.port_combo.setEnabled(False)
                self.baud_combo.setEnabled(False)
            except Exception as e:
                self._log(f"[ERROR] 连接失败：{e}")
                self.btn_connect.setChecked(False)
        else:
            if self._serial:
                self._serial.close()
                self._serial = None
            self._log("[INFO] 已断开")
            self.btn_connect.setText("连接")
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)

    def _on_send(self):
        cmd = self.cmd_edit.text().strip()
        if not cmd:
            return
        self._send_quick(cmd)
        self.cmd_edit.clear()

    def _send_quick(self, cmd):
        if not self._serial:
            self._log("[ERROR] 请先连接串口")
            return
        try:
            self._serial.write((cmd + "\n").encode("utf-8"))
            self._serial.flush()
            self._log(f"[TX] {cmd}")
            resp = self._serial.readline()
            if resp:
                self._log(f"[RX] {resp.decode('utf-8').strip()}")
            else:
                self._log("[RX] (无响应)")
        except Exception as e:
            self._log(f"[ERROR] {e}")

    def closeEvent(self, event):
        if self._serial:
            self._serial.close()
        event.accept()


# ── 棋盘格生成对话框 ──────────────────────────────

class CheckerboardDialog(QDialog):
    """棋盘格生成对话框：设行列数和方格尺寸 -> 生成 PNG/PDF。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("生成棋盘格")
        self.setMinimumWidth(400)
        self.setStyleSheet(_dialog_stylesheet())
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 参数
        param_group = QGroupBox("棋盘格参数")
        form = QFormLayout(param_group)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(3, 20)
        self.cols_spin.setValue(11)
        form.addRow("列数（格子）", self.cols_spin)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(3, 20)
        self.rows_spin.setValue(8)
        form.addRow("行数（格子）", self.rows_spin)

        self.square_spin = QDoubleSpinBox()
        self.square_spin.setRange(5.0, 50.0)
        self.square_spin.setValue(18.0)
        self.square_spin.setSuffix(" mm")
        form.addRow("方格尺寸", self.square_spin)
        layout.addWidget(param_group)

        # 按钮
        btn_layout = QHBoxLayout()
        self.btn_png = QPushButton("生成 PNG")
        self.btn_png.setStyleSheet(_btn_style(_BTN_PRIMARY))
        self.btn_png.clicked.connect(self._on_generate_png)
        btn_layout.addWidget(self.btn_png)

        self.btn_pdf = QPushButton("生成 PDF")
        self.btn_pdf.setStyleSheet(_btn_style(_BTN_NEUTRAL))
        self.btn_pdf.clicked.connect(self._on_generate_pdf)
        btn_layout.addWidget(self.btn_pdf)
        layout.addLayout(btn_layout)

        # 结果
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(100)
        self.result_text.setStyleSheet(
            "background-color: #2d2d2d; color: #33d17a;"
            " border-radius: 6px; font-family: monospace; font-size: 12px;"
        )
        layout.addWidget(self.result_text)

    def _log(self, msg):
        self.result_text.append(msg)

    def _on_generate_png(self):
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        square = self.square_spin.value()

        path, _ = QFileDialog.getSaveFileName(
            self, "保存棋盘格", "checkerboard.png", "PNG Files (*.png)"
        )
        if not path:
            return

        try:
            from generate_checkerboard import CheckerboardGenerator
            gen = CheckerboardGenerator()
            result = gen.generate_opencv_checkerboard(
                rows=rows, cols=cols, square_size_mm=square,
                save_path=path,
            )
            self._log(f"<<< 已生成：{result[0]}")
            self._log(f"    内角点：{result[1][0]}x{result[1][1]}")
            self._log(f"    代码中使用：checkerboard_size={result[1]}")
        except Exception as e:
            self._log(f"!!! 异常：{e}")

    def _on_generate_pdf(self):
        rows = self.rows_spin.value()
        cols = self.cols_spin.value()
        square = self.square_spin.value()

        path, _ = QFileDialog.getSaveFileName(
            self, "保存棋盘格", "checkerboard.pdf", "PDF Files (*.pdf)"
        )
        if not path:
            return

        try:
            from generate_checkerboard import CheckerboardGenerator
            gen = CheckerboardGenerator()
            result = gen.generate_matplotlib_checkerboard(
                rows=rows, cols=cols, square_size_mm=square,
                save_path=path,
            )
            self._log(f"<<< 已生成：{result[0]}")
            self._log(f"    内角点：{result[1][0]}x{result[1][1]}")
        except ImportError:
            self._log("!!! 需要 matplotlib：pip install matplotlib")
        except Exception as e:
            self._log(f"!!! 异常：{e}")
