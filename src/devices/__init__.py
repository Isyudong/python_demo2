"""
设备包。从 src.devices.factory 导入 create_camera / create_arduino / get_mode。
"""

from src.devices.factory import create_camera, create_arduino

__all__ = ['create_camera', 'create_arduino']
