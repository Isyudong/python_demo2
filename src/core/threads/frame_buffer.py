"""帧缓存 — 相机线程写入，检测 Worker / 预览消费。"""

import threading


class FrameBuffer:
    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None
        self._timestamp = 0.0

    def put(self, frame, timestamp):
        with self._lock:
            self._frame = frame
            self._timestamp = timestamp

    def get(self):
        """返回 (frame_copy, timestamp)，取不到返回 (None, 0)。"""
        with self._lock:
            if self._frame is None:
                return None, 0.0
            return self._frame.copy(), self._timestamp
