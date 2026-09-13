"""设备相关的基础定义。"""

from enum import Enum


class DeviceState(Enum):
    """设备状态。"""

    IDLE = "idle"
    BUSY = "busy"
    ALARM = "alarm"
    DISCONNECTED = "disconnected"


class DeviceBase:
    """带日志回调的设备基类，Sim / Real 实现共用。"""

    def __init__(self, message_callback=None):
        self._msg_cb = message_callback

    def set_message_callback(self, cb):
        self._msg_cb = cb

    def _log(self, msg):
        if self._msg_cb:
            self._msg_cb(msg)
        else:
            print(msg)
