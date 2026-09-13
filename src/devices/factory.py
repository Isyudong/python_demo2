"""
设备工厂 — 根据配置创建 Sim 或 Real 实例。
"""

from config import get_mode


def create_camera():
    if get_mode() == "real":
        from src.devices.real_impl import RealCamera
        return RealCamera()
    else:
        from src.devices.sim_impl import SimCamera
        return SimCamera()


def create_arduino(message_callback=None):
    if get_mode() == "real":
        from src.devices.real_impl import RealArduino
        return RealArduino(message_callback=message_callback)
    else:
        from src.devices.sim_impl import SimArduino
        return SimArduino(message_callback=message_callback)



