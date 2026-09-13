"""
黄鳝鱼卵剔除系统主入口。
支持 --sim / --real 命令行参数切换运行模式。
"""

import sys
import os


from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from config import set_mode

if "--real" in sys.argv:
    mode = "real"
elif "--sim" in sys.argv:
    mode = "sim"
else:
    mode = "sim"

set_mode(mode)


def main():
    print("=" * 60)
    print("       黄鳝鱼卵剔除系统v1.0")
    print("=" * 60)
    print(f"运行模式：{mode.upper()}")
    if mode == "sim":
        print("  （无需硬件，相机从指定位置读图）")
    else:
        print("  （需要连接相机和 Arduino）")
    print("=" * 60)

    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontUseNativeMenuBar, True)

    from src.ui.app_window import MainWindow
    win = MainWindow()
    win.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
