"""主窗口。"""

import time
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, QApplication, QFileDialog, QMessageBox,
    QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QWidget,
    QLabel, QTextEdit, QGroupBox, QSizePolicy, QStackedWidget,
)
from PySide6.QtGui import QImage, QPixmap, QAction
from PySide6.QtCore import Qt, QTimer

import cv2

from src.core.workflow import Workflow
from config import get_config, save_config
from src.ui.tool_dialogs import (
    CalibDialog, ScaleDialog, SerialTestDialog, CheckerboardDialog,
)

_BG          = "#f6f5f4"
_CARD_BG     = "#ffffff"
_BORDER      = "#e0e0e0"
_TEXT        = "#2d2d2d"
_TEXT_MUTED  = "#888888"
_PRIMARY     = "#3584e4"
_DANGER      = "#e01b24"
_SUCCESS     = "#33d17a"
_VIDEO_BG    = "#1a1a1a"
_LOG_BG      = "#1e1e1e"
_LOG_FG      = "#33d17a"
def _groupbox_style():
    return (
        f"QGroupBox {{"
        f"  background-color: {_CARD_BG};"
        f"  border: 1px solid {_BORDER};"
        f"  border-radius: 8px;"
        f"  margin-top: 12px;"
        f"  padding: 16px 8px 8px 8px;"
        f"  font-size: 13px;"
        f"}}"
        f"QGroupBox::title {{"
        f"  subcontrol-origin: margin;"
        f"  left: 12px;"
        f"  padding: 0 6px;"
        f"  color: {_TEXT};"
        f"  background-color: {_CARD_BG};"
        f"}}"
    )


def _btn_style(color):
    return (
        f"QPushButton {{"
        f"  background-color: {color};"
        f"  color: white;"
        f"  border: none;"
        f"  border-radius: 6px;"
        f"  padding: 8px 16px;"
        f"  font-size: 13px;"
        f"}}"
        f"QPushButton:hover {{ background-color: {color}dd; }}"
        f"QPushButton:pressed {{ background-color: {color}bb; }}"
        f"QPushButton:disabled {{ background-color: #ccc; }}"
    )


def _input_style():
    return (
        f"QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{"
        f"  border: 1px solid #d0d0d0;"
        f"  border-radius: 4px;"
        f"  padding: 4px 8px;"
        f"  background-color: white;"
        f"  color: {_TEXT};"
        f"  font-size: 13px;"
        f"}}"
        f"QLineEdit:focus, QSpinBox:focus, "
        f"QDoubleSpinBox:focus, QComboBox:focus {{"
        f"  border-color: {_PRIMARY};"
        f"}}"
    )


def _label_style():
    return f"color: {_TEXT}; background-color: transparent;"


def _value_style():
    return (f"color: {_TEXT}; font-weight: 500;"
            f" background-color: transparent;")
class MainWindow(QMainWindow):
    """主窗口。"""

    def __init__(self):
        super().__init__()
        self._start_time = None

        self.setWindowTitle("黄鳝鱼卵剔除系统")
        self.resize(1280, 760)
        self.setStyleSheet(
            f"QMainWindow {{ background-color: {_BG}; }}"
        )

        self._build_menu()
        self._build_pages()

        self._workflow = Workflow(
            on_frame=self._on_frame,
            on_log=self.log_message,
            on_detection_result=self._on_detection_result,
        )

        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._on_status_tick)
        self._status_timer.start(500)

        self._startup()

    def _build_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar {{ background-color: {_BG}; color: {_TEXT}; }}"
            f"QMenuBar::item:selected {{ background-color: #ddd; }}"
            f"QMenu {{ background-color: white; color: {_TEXT};"
            f" border: 1px solid {_BORDER}; }}"
            f"QMenu::item:selected {{ background-color: {_PRIMARY};"
            f" color: white; }}"
        )

        tools_menu = mb.addMenu("工具(&T)")
        tools_menu.addAction(
            QAction("相机标定...", self, triggered=self._open_calib))
        tools_menu.addAction(
            QAction("像素比例计算...", self, triggered=self._open_scale))
        tools_menu.addAction(
            QAction("串口测试...", self, triggered=self._open_serial))
        tools_menu.addAction(
            QAction("生成棋盘格...", self,
                    triggered=self._open_checkerboard))

        mode_menu = mb.addMenu("模式(&M)")
        mode_menu.addAction(
            QAction("普通模式", self,
                    triggered=lambda: self._switch_mode("normal")))
        mode_menu.addAction(
            QAction("专家模式", self,
                    triggered=lambda: self._switch_mode("expert")))

        win_menu = mb.addMenu("窗口(&W)")
        win_menu.addAction(
            QAction("全屏", self, triggered=self._toggle_fullscreen))
        win_menu.addAction(
            QAction("恢复正常", self, triggered=self._restore_window))

    def _build_pages(self):
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {_BG};")

        self._normal_page = self._create_normal_page()
        self._expert_page = self._create_expert_page()

        self._stack.addWidget(self._normal_page)
        self._stack.addWidget(self._expert_page)
        self.setCentralWidget(self._stack)

    def _switch_mode(self, mode):
        if mode == "normal":
            self._stack.setCurrentWidget(self._normal_page)
            self.log_message("切换到普通模式")
        else:
            self._stack.setCurrentWidget(self._expert_page)
            self._load_params_to_ui()
            self.log_message("切换到专家模式")

    def _create_normal_page(self):
        page = QWidget()
        page.setStyleSheet(f"background-color: {_BG};")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        left = QVBoxLayout()
        left.setSpacing(8)

        self.video_label = QLabel("视频预览区域")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet(
            f"background-color: {_VIDEO_BG}; color: #888;"
            f" border-radius: 8px; font-size: 14px;"
        )
        self.video_label.setMinimumSize(640, 400)
        self.video_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        left.addWidget(self.video_label, 1)

        self.msg_area = QTextEdit()
        self.msg_area.setReadOnly(True)
        self.msg_area.setMaximumHeight(120)
        self.msg_area.setStyleSheet(
            f"background-color: {_LOG_BG}; color: {_LOG_FG};"
            f" border-radius: 8px; font-family: monospace;"
            f" font-size: 12px; border: none;"
        )
        left.addWidget(self.msg_area)

        left_widget = QWidget()
        left_widget.setLayout(left)
        layout.addWidget(left_widget, 1)

        right = QVBoxLayout()
        right.setSpacing(8)
        right.setContentsMargins(0, 0, 0, 0)

        status_group = QGroupBox("状态信息")
        status_group.setStyleSheet(_groupbox_style())
        status_grid = QGridLayout(status_group)
        status_grid.setContentsMargins(8, 8, 8, 8)
        status_grid.setHorizontalSpacing(16)
        status_grid.setVerticalSpacing(6)

        self.status_labels = {}
        for i, (key, label) in enumerate([
            ("detect",  "检测状态"),
            ("cam",     "相机"),
            ("arduino", "下位机"),
            ("count",   "检测数量"),
            ("time",    "运行时间"),
            ("motor_x", "电机 X"),
            ("motor_y", "电机 Y"),
        ]):
            lbl = QLabel(label)
            lbl.setStyleSheet(_label_style())
            status_grid.addWidget(lbl, i, 0, Qt.AlignLeft)
            val = QLabel("—")
            val.setStyleSheet(_value_style())
            val.setAlignment(Qt.AlignRight)
            self.status_labels[key] = val
            status_grid.addWidget(val, i, 1, Qt.AlignRight)

        # 初始化检测状态
        self.status_labels["detect"].setText("● 未运行")
        self.status_labels["detect"].setStyleSheet(
            f"color: {_TEXT_MUTED}; font-weight: 500;"
            f" background-color: transparent;"
        )
        right.addWidget(status_group)

        right.addStretch()

        op_group = QGroupBox("操作控制")
        op_group.setStyleSheet(_groupbox_style())
        op_layout = QVBoxLayout(op_group)
        op_layout.setSpacing(8)
        op_layout.setContentsMargins(8, 8, 8, 8)

        self.btn_camera = QPushButton("连接相机")
        self.btn_camera.setStyleSheet(_btn_style(_PRIMARY))
        self.btn_camera.setMinimumHeight(40)
        self.btn_camera.clicked.connect(self._on_toggle_camera)
        op_layout.addWidget(self.btn_camera)

        self.btn_detect = QPushButton("开始检测")
        self.btn_detect.setStyleSheet(_btn_style(_SUCCESS))
        self.btn_detect.setMinimumHeight(40)
        self.btn_detect.clicked.connect(self._on_toggle_detect)
        op_layout.addWidget(self.btn_detect)

        self.btn_stop = QPushButton("急停")
        self.btn_stop.setStyleSheet(_btn_style(_DANGER))
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.clicked.connect(self._on_emergency_stop)
        op_layout.addWidget(self.btn_stop)

        right.addWidget(op_group)

        right_widget = QWidget()
        right_widget.setLayout(right)
        right_widget.setFixedWidth(300)
        layout.addWidget(right_widget)

        return page

    def _create_expert_page(self):
        page = QWidget()
        page.setStyleSheet(f"background-color: {_BG};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 紧凑状态条
        status_bar = QWidget()
        status_bar.setStyleSheet(
            f"background-color: {_CARD_BG};"
            f" border: 1px solid {_BORDER};"
            f" border-radius: 8px;"
        )
        bar_layout = QHBoxLayout(status_bar)
        bar_layout.setContentsMargins(12, 6, 12, 6)
        bar_layout.setSpacing(16)

        self.expert_status = {}
        for key, label in [
            ("cam", "相机"), ("arduino", "下位机"),
            ("motor", "电机"), ("count", "检测"),
            ("time", "时间"),
        ]:
            lbl = QLabel(f"{label}: —")
            lbl.setStyleSheet(
                f"color: {_TEXT_MUTED}; font-size: 12px;"
                f" background-color: transparent;"
            )
            self.expert_status[key] = lbl
            bar_layout.addWidget(lbl)
        bar_layout.addStretch()
        layout.addWidget(status_bar)

        # 参数卡片网格（2 列）
        grid = QGridLayout()
        grid.setSpacing(8)

        grid.addWidget(self._create_detection_card(), 0, 0)
        grid.addWidget(self._create_hsv_card(),       0, 1)
        grid.addWidget(self._create_camera_card(),    1, 0)
        grid.addWidget(self._create_arduino_card(),   1, 1)
        grid.addWidget(self._create_roi_card(),       2, 0)
        grid.addWidget(self._create_jog_card(),       2, 1)

        layout.addLayout(grid, 1)

        # 原始指令（调试）— 全宽
        layout.addWidget(self._create_raw_card())

        return page

    def _create_detection_card(self):
        group = QGroupBox("检测参数")
        group.setStyleSheet(_groupbox_style() + _input_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.exp_dp = QDoubleSpinBox()
        self.exp_dp.setRange(0.1, 10.0)
        self.exp_dp.setValue(1.5)
        self._add_param_row(layout, "dp", self.exp_dp)

        self.exp_min_dist = QSpinBox()
        self.exp_min_dist.setRange(1, 1000)
        self.exp_min_dist.setValue(30)
        self._add_param_row(layout, "min_dist", self.exp_min_dist)

        self.exp_param1 = QSpinBox()
        self.exp_param1.setRange(1, 500)
        self.exp_param1.setValue(100)
        self._add_param_row(layout, "param1", self.exp_param1)

        self.exp_param2 = QSpinBox()
        self.exp_param2.setRange(1, 500)
        self.exp_param2.setValue(40)
        self._add_param_row(layout, "param2", self.exp_param2)

        self.exp_min_r = QSpinBox()
        self.exp_min_r.setRange(0, 1000)
        self.exp_min_r.setValue(5)
        self._add_param_row(layout, "min_radius", self.exp_min_r)

        self.exp_max_r = QSpinBox()
        self.exp_max_r.setRange(0, 1000)
        self.exp_max_r.setValue(20)
        self._add_param_row(layout, "max_radius", self.exp_max_r)

        btn = QPushButton("应用")
        btn.setStyleSheet(_btn_style(_PRIMARY))
        btn.clicked.connect(self._apply_detection_params)
        layout.addWidget(btn)
        return group

    def _create_hsv_card(self):
        group = QGroupBox("HSV 颜色筛选")
        group.setStyleSheet(_groupbox_style() + _input_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.exp_h_min = QSpinBox()
        self.exp_h_min.setRange(0, 180)
        self.exp_h_min.setValue(20)
        self._add_param_row(layout, "H 最小值", self.exp_h_min)

        self.exp_h_max = QSpinBox()
        self.exp_h_max.setRange(0, 180)
        self.exp_h_max.setValue(30)
        self._add_param_row(layout, "H 最大值", self.exp_h_max)

        self.exp_s_min = QSpinBox()
        self.exp_s_min.setRange(0, 255)
        self.exp_s_min.setValue(100)
        self._add_param_row(layout, "S 最小值", self.exp_s_min)

        self.exp_v_min = QSpinBox()
        self.exp_v_min.setRange(0, 255)
        self.exp_v_min.setValue(100)
        self._add_param_row(layout, "V 最小值", self.exp_v_min)

        btn = QPushButton("应用")
        btn.setStyleSheet(_btn_style(_PRIMARY))
        btn.clicked.connect(self._apply_hsv_params)
        layout.addWidget(btn)
        return group

    def _create_camera_card(self):
        group = QGroupBox("相机参数")
        group.setStyleSheet(_groupbox_style() + _input_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.exp_resolution = QComboBox()
        self.exp_resolution.addItems(
            ["原始分辨率", "640x480", "1280x720", "1920x1080"])
        self._add_param_row(layout, "分辨率", self.exp_resolution)

        self.exp_exposure = QSpinBox()
        self.exp_exposure.setRange(1, 100000)
        self.exp_exposure.setValue(30)
        self.exp_exposure.setSuffix(" ms")
        self._add_param_row(layout, "曝光时间", self.exp_exposure)

        btn = QPushButton("应用")
        btn.setStyleSheet(_btn_style(_PRIMARY))
        btn.clicked.connect(self._apply_camera_params)
        layout.addWidget(btn)
        return group

    def _create_arduino_card(self):
        group = QGroupBox("下位机参数")
        group.setStyleSheet(_groupbox_style() + _input_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.exp_port = QComboBox()
        self.exp_port.setEditable(True)
        for p in ["/dev/ttyUSB0", "/dev/ttyUSB1",
                   "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyS0"]:
            self.exp_port.addItem(p)
        self._add_param_row(layout, "串口", self.exp_port)

        self.exp_baud = QComboBox()
        for b in ["9600", "57600", "115200"]:
            self.exp_baud.addItem(b)
        self.exp_baud.setCurrentText("115200")
        self._add_param_row(layout, "波特率", self.exp_baud)

        btn = QPushButton("应用")
        btn.setStyleSheet(_btn_style(_PRIMARY))
        btn.clicked.connect(self._apply_arduino_params)
        layout.addWidget(btn)
        return group

    def _create_roi_card(self):
        group = QGroupBox("ROI 管理")
        group.setStyleSheet(_groupbox_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self.roi_count_label = QLabel("ROI 数量：0")
        self.roi_count_label.setStyleSheet(_label_style())
        layout.addWidget(self.roi_count_label)

        self.ratio_label = QLabel("像素/毫米：—")
        self.ratio_label.setStyleSheet(_label_style())
        layout.addWidget(self.ratio_label)

        btn_load = QPushButton("加载 ROI")
        btn_load.setStyleSheet(_btn_style(_PRIMARY))
        btn_load.clicked.connect(self._on_load_roi)
        layout.addWidget(btn_load)

        btn_clear = QPushButton("清除 ROI")
        btn_clear.setStyleSheet(_btn_style("#999999"))
        btn_clear.clicked.connect(self._on_clear_roi)
        layout.addWidget(btn_clear)

        layout.addStretch()
        return group

    def _create_jog_card(self):
        group = QGroupBox("手动控制")
        group.setStyleSheet(_groupbox_style() + _input_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        self.jog_step = QDoubleSpinBox()
        self.jog_step.setRange(0.1, 100.0)
        self.jog_step.setValue(1.0)
        self.jog_step.setSuffix(" mm")
        self._add_param_row(layout, "步长", self.jog_step)

        # X 轴一行
        x_row = QHBoxLayout()
        x_lbl = QLabel("X 轴")
        x_lbl.setStyleSheet(_label_style())
        x_lbl.setFixedWidth(40)
        x_row.addWidget(x_lbl)
        btn_xm = QPushButton("X-")
        btn_xm.setStyleSheet(_btn_style(_PRIMARY))
        btn_xm.clicked.connect(
            lambda: self._on_jog(-self.jog_step.value(), 0))
        x_row.addWidget(btn_xm)
        btn_xp = QPushButton("X+")
        btn_xp.setStyleSheet(_btn_style(_PRIMARY))
        btn_xp.clicked.connect(
            lambda: self._on_jog(self.jog_step.value(), 0))
        x_row.addWidget(btn_xp)
        layout.addLayout(x_row)

        # Y 轴一行
        y_row = QHBoxLayout()
        y_lbl = QLabel("Y 轴")
        y_lbl.setStyleSheet(_label_style())
        y_lbl.setFixedWidth(40)
        y_row.addWidget(y_lbl)
        btn_ym = QPushButton("Y-")
        btn_ym.setStyleSheet(_btn_style(_PRIMARY))
        btn_ym.clicked.connect(
            lambda: self._on_jog(0, -self.jog_step.value()))
        y_row.addWidget(btn_ym)
        btn_yp = QPushButton("Y+")
        btn_yp.setStyleSheet(_btn_style(_PRIMARY))
        btn_yp.clicked.connect(
            lambda: self._on_jog(0, self.jog_step.value()))
        y_row.addWidget(btn_yp)
        layout.addLayout(y_row)

        layout.addStretch()
        return group

    def _create_raw_card(self):
        group = QGroupBox("原始指令（调试）")
        group.setStyleSheet(_groupbox_style() + _input_style())
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        # 输入行
        cmd_row = QHBoxLayout()
        self.raw_input = QLineEdit()
        self.raw_input.setPlaceholderText("输入指令，如: G0 X10 Y10")
        self.raw_input.returnPressed.connect(self._on_send_raw)
        cmd_row.addWidget(self.raw_input)
        btn_send = QPushButton("发送")
        btn_send.setStyleSheet(_btn_style(_PRIMARY))
        btn_send.clicked.connect(self._on_send_raw)
        cmd_row.addWidget(btn_send)
        layout.addLayout(cmd_row)

        # 消息显示框
        self.raw_display = QTextEdit()
        self.raw_display.setReadOnly(True)
        self.raw_display.setMaximumHeight(120)
        self.raw_display.setStyleSheet(
            f"background-color: {_LOG_BG}; color: {_LOG_FG};"
            f" border-radius: 6px; font-family: monospace;"
            f" font-size: 12px; border: 1px solid {_BORDER};"
        )
        layout.addWidget(self.raw_display)

        return group

    def _add_param_row(self, parent_layout, label_text, widget):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(_label_style())
        row.addWidget(lbl)
        row.addStretch()
        widget.setFixedWidth(140)
        row.addWidget(widget)
        parent_layout.addLayout(row)

    def _startup(self):
        self.log_message("系统启动中...")
        self._workflow.auto_detect_hardware()
        self._start_time = time.time()
        self._update_status_display()

        if self._workflow.is_camera_connected:
            self.btn_camera.setText("断开相机")
            self._workflow.start_live_view()
            self.log_message("实时预览已开始")

    def _on_status_tick(self):
        """仅更新运行时间和电机位置（不再拉帧）。"""
        self._update_runtime()
        self._update_motor_position()

    def _update_runtime(self):
        if not self._start_time:
            return
        elapsed = int(time.time() - self._start_time)
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
        if "time" in self.status_labels:
            self.status_labels["time"].setText(time_str)
        if "time" in self.expert_status:
            self.expert_status["time"].setText(f"时间: {time_str}")

    def _update_motor_position(self):
        pos = self._workflow.query_motor_position()
        if pos:
            x_str, y_str = f"{pos['x']:.2f}", f"{pos['y']:.2f}"
            if "motor_x" in self.status_labels:
                self.status_labels["motor_x"].setText(x_str)
                self.status_labels["motor_y"].setText(y_str)
            if "motor" in self.expert_status:
                self.expert_status["motor"].setText(
                    f"电机: X={x_str} Y={y_str}")
        else:
            if "motor_x" in self.status_labels:
                self.status_labels["motor_x"].setText("—")
                self.status_labels["motor_y"].setText("—")
            if "motor" in self.expert_status:
                self.expert_status["motor"].setText("电机: —")

    def _update_status_display(self):
        cam = self._workflow.is_camera_connected
        ard = self._workflow.is_arduino_connected

        cam_text = "● 已连接" if cam else "● 未连接"
        cam_color = _SUCCESS if cam else _DANGER
        ard_text = "● 已连接" if ard else "● 未连接"
        ard_color = _SUCCESS if ard else _DANGER

        if "cam" in self.status_labels:
            self.status_labels["cam"].setText(cam_text)
            self.status_labels["cam"].setStyleSheet(
                f"color: {cam_color}; font-weight: 500;"
                f" background-color: transparent;"
            )
        if "arduino" in self.status_labels:
            self.status_labels["arduino"].setText(ard_text)
            self.status_labels["arduino"].setStyleSheet(
                f"color: {ard_color}; font-weight: 500;"
                f" background-color: transparent;"
            )
        if "cam" in self.expert_status:
            self.expert_status["cam"].setText(
                f"相机: {'连接' if cam else '未连接'}")
        if "arduino" in self.expert_status:
            self.expert_status["arduino"].setText(
                f"下位机: {'连接' if ard else '未连接'}")

    def _on_toggle_camera(self):
        if self._workflow.is_camera_connected:
            self._workflow.stop_live_view()
            self._workflow.stop_camera()
            self.btn_camera.setText("连接相机")
            self.video_label.clear()
            self.video_label.setText("视频预览区域")
            self.log_message("相机已断开")
        else:
            ok = self._workflow.start_camera()
            if ok:
                self._workflow.start_live_view()
                self.btn_camera.setText("断开相机")
                self.log_message("相机已连接，实时预览已开始")
            else:
                self.log_message("相机连接失败")
        self._update_status_display()

    def _on_toggle_detect(self):
        if not self._workflow.is_camera_connected:
            QMessageBox.warning(self, "提示", "请先连接相机")
            return
        self.log_message("正在检测当前帧...")
        self._workflow.trigger_detection()

    def _on_emergency_stop(self):
        self._workflow.abort()
        self._workflow.stop_motors()
        self.log_message("!!! 紧急停止已触发，已发送中止指令 !!!")

    def _load_params_to_ui(self):
        """刷新专家模式参数。"""
        det = self._workflow.get_detection_params()
        self.exp_dp.setValue(det.get('dp', 1.5))
        self.exp_min_dist.setValue(det.get('min_dist', 30))
        self.exp_param1.setValue(det.get('param1', 100))
        self.exp_param2.setValue(det.get('param2', 40))
        self.exp_min_r.setValue(det.get('min_radius', 5))
        self.exp_max_r.setValue(det.get('max_radius', 20))

        hsv = self._workflow.get_hsv_params()
        self.exp_h_min.setValue(hsv.get('h_min', 20))
        self.exp_h_max.setValue(hsv.get('h_max', 30))
        self.exp_s_min.setValue(hsv.get('s_min', 100))
        self.exp_v_min.setValue(hsv.get('v_min', 100))

        cfg = get_config()
        cam_cfg = cfg.get('camera', {})
        self.exp_exposure.setValue(
            cam_cfg.get('exposure_time', 30000) // 1000)

        ser_cfg = cfg.get('serial', {})
        self.exp_port.setCurrentText(
            ser_cfg.get('port', '/dev/ttyUSB0'))
        self.exp_baud.setCurrentText(
            str(ser_cfg.get('baudrate', 115200)))

        self.roi_count_label.setText(
            f"ROI 数量：{self._workflow.get_roi_count()}")
        info = self._workflow.get_conversion_info()
        self.ratio_label.setText(
            f"像素/毫米：{info['pixels_per_mm']:.2f}")

    def _apply_detection_params(self):
        params = {
            'dp': self.exp_dp.value(),
            'min_dist': self.exp_min_dist.value(),
            'param1': self.exp_param1.value(),
            'param2': self.exp_param2.value(),
            'min_radius': self.exp_min_r.value(),
            'max_radius': self.exp_max_r.value(),
        }
        self._workflow.set_detection_params(params)
        self.log_message(f"检测参数已应用")

    def _apply_hsv_params(self):
        params = {
            'h_min': self.exp_h_min.value(),
            'h_max': self.exp_h_max.value(),
            's_min': self.exp_s_min.value(),
            'v_min': self.exp_v_min.value(),
        }
        self._workflow.set_hsv_params(params)
        self.log_message("HSV 参数已应用")

    def _apply_camera_params(self):
        self._workflow.set_exposure(self.exp_exposure.value())
        cfg = get_config()
        res_text = self.exp_resolution.currentText()
        if res_text != "原始分辨率":
            w, h = map(int, res_text.split('x'))
            cfg['camera']['target_resolution'] = (w, h)
        else:
            cfg['camera']['target_resolution'] = None
        self.log_message("相机参数已应用")

    def _apply_arduino_params(self):
        port = self.exp_port.currentText()
        baudrate = int(self.exp_baud.currentText())
        self._workflow.set_serial_config(port, baudrate)
        self.log_message(f"下位机参数已应用：{port} @ {baudrate}")

    def _on_load_roi(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 ROI 文件", "",
            "Text Files (*.txt);;All Files (*)")
        if path:
            rois = self._workflow.load_rois(path)
            self.roi_count_label.setText(f"ROI 数量：{len(rois)}")

    def _on_clear_roi(self):
        self._workflow.clear_rois()
        self.roi_count_label.setText("ROI 数量：0")

    def _on_jog(self, dx, dy):
        ok = self._workflow.jog_move(dx, dy)
        if ok:
            self.log_message(f"Jog: dx={dx:.1f} mm, dy={dy:.1f} mm")
        else:
            self.log_message("Jog 失败：下位机未连接")

    def _on_send_raw(self):
        cmd = self.raw_input.text().strip()
        if not cmd:
            return
        self.raw_input.clear()
        self.raw_display.append(f"[TX] {cmd}")
        resp = self._workflow.send_raw(cmd)
        if resp:
            self.raw_display.append(f"[RX] {resp}")
        else:
            self.raw_display.append("[RX] (无响应)")

    def _open_calib(self):
        CalibDialog(self).exec()

    def _open_scale(self):
        ScaleDialog(self).exec()

    def _open_serial(self):
        SerialTestDialog(self).exec()

    def _open_checkerboard(self):
        CheckerboardDialog(self).exec()

    def _toggle_fullscreen(self):
        self.showFullScreen()

    def _restore_window(self):
        self.showNormal()
        self.resize(1280, 760)

    def log_message(self, msg):
        now = datetime.now().strftime("%H:%M:%S")
        self.msg_area.append(f"[{now}] {msg}")

    def display_frame(self, img):
        """BGR ndarray → QImage → 显示（检测结果路径）。"""
        if img is None:
            return
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, w * ch, QImage.Format_RGB888)
        self._show_qimage(qimg)

    def _show_qimage(self, qimg):
        """贴 QImage 到 video_label。"""
        if qimg is None:
            return
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)

    def _on_frame(self, qimg):
        """相机线程推送 QImage（已做 BGR→RGB 转换）。"""
        self._show_qimage(qimg)

    def _on_detection_result(self, circles, annotated_image, circles_mm=None):
        count = len(circles)
        if "count" in self.status_labels:
            self.status_labels["count"].setText(str(count))
        if "count" in self.expert_status:
            self.expert_status["count"].setText(f"检测: {count}")

        if count > 0:
            self.status_labels["detect"].setText(f"● 已检测 {count} 个")
            self.status_labels["detect"].setStyleSheet(
                f"color: {_SUCCESS}; font-weight: 500;"
                f" background-color: transparent;")
            self.log_message(f"检测完成：发现 {count} 个目标")
            self.display_frame(annotated_image)
            if circles_mm:
                self._workflow.send_targets(circles_mm)
        else:
            self.status_labels["detect"].setText("● 无目标")
            self.status_labels["detect"].setStyleSheet(
                f"color: {_TEXT_MUTED}; font-weight: 500;"
                f" background-color: transparent;")
            self.log_message("检测完成：未发现目标")
            QTimer.singleShot(5000, self._restore_preview)

    def _restore_preview(self):
        """恢复实时预览。"""
        self.status_labels["detect"].setText("● 就绪")
        self.status_labels["detect"].setStyleSheet(
            f"color: {_TEXT_MUTED}; font-weight: 500;"
            f" background-color: transparent;")

    def closeEvent(self, event):
        self._status_timer.stop()
        self._workflow.stop_comm_thread()
        self._workflow.stop_camera_thread()
        self._workflow.stop_writer_thread()
        if self._workflow._detect_thread is not None and self._workflow._detect_thread.isRunning():
            self._workflow._detect_thread.quit()
            self._workflow._detect_thread.wait(3000)
        self._workflow.stop_camera()
        if self._workflow.is_arduino_connected:
            self._workflow.disconnect_arduino()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
