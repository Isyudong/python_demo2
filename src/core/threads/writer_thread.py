"""写盘线程 —— 常驻运行，异步执行 WriterTask。

职责：
- 阻塞等待 WriterTask 队列
- 异步存图（cv2.imwrite）/ 存 JSON
- 消费 shutdown 毒丸优雅退出
- 限队列长度防止内存溢出
"""

import time
import queue
import json

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from src.core.messages import WriterTask
from config import get_config


class WriterThread(QThread):
    """写盘线程。

    Qt 信号：
        task_done(str)  — "image: path" / "json: path"
        error(str)      — 写盘失败

    Python 回调（无需 QApplication）：
        set_done_callback(fn)
        set_error_callback(fn)
    """

    task_done = Signal(str)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = get_config()
        writer_cfg = cfg.get('writer', {})
        self._max_queue = writer_cfg.get('max_queue', 50)
        self._queue = queue.Queue(maxsize=self._max_queue)
        self._running = False
        self._cb_done = None
        self._cb_error = None

    def set_done_callback(self, fn):
        self._cb_done = fn

    def set_error_callback(self, fn):
        self._cb_error = fn

    def submit(self, task):
        """主线程调用：投递写盘任务（非阻塞，队列满时丢弃并告警）。"""
        if not isinstance(task, WriterTask):
            raise TypeError("需要 WriterTask 实例")
        try:
            self._queue.put_nowait(task)
        except queue.Full:
            self.error.emit("写盘队列已满，丢弃任务")

    def stop(self):
        """发送 shutdown 毒丸并等待线程退出。"""
        self._running = False
        try:
            self._queue.put_nowait(WriterTask('shutdown'))
        except queue.Full:
            pass
        if not self.wait(3000):
            self.terminate()
            self.wait(1000)

    def run(self):
        """主循环。"""
        self._running = True
        while self._running:
            try:
                task = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if task.task_type == 'shutdown':
                break

            try:
                self._execute(task)
            except Exception as e:
                self._emit_error(f"写盘失败：{e}")

    # ── 执行 ────────────────────────────────────────────

    def _execute(self, task):
        if task.task_type == 'image' and task.data:
            img, filepath = task.data
            self._save_image(np.asarray(img), filepath)
            self._emit_done(f"image: {filepath}")
        elif task.task_type == 'json' and task.data:
            data, filepath = task.data
            self._save_json(data, filepath)
            self._emit_done(f"json: {filepath}")

    @staticmethod
    def _save_image(img, filepath):
        cv2.imwrite(str(filepath), img)

    @staticmethod
    def _save_json(data, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 双通道通知 ──────────────────────────────────────

    def _emit_done(self, msg):
        if self._cb_done:
            try:
                self._cb_done(msg)
            except Exception:
                pass
        self.task_done.emit(msg)

    def _emit_error(self, msg):
        if self._cb_error:
            try:
                self._cb_error(msg)
            except Exception:
                pass
        self.error.emit(msg)
