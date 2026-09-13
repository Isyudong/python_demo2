"""通信线程 —— 常驻运行，处理 CommRequest 队列。

职责：
- 阻塞等待 CommRequest 队列中的任务
- 按协议序列与下位机交互（BATCH_START → TARGET... → BATCH_COMPLETE）
- 发射 comm_status 信号给 UI
- 支持 ABORT 插队（高优先级清空队列后执行）
"""

import time
import queue

from PySide6.QtCore import QThread, Signal

from src.core.messages import CommStatus, CommRequest
from config import get_config


class CommThread(QThread):
    """通信线程。

    信号（Qt 方式，需 QApplication 事件循环）：
        status_updated(CommStatus)  — 状态更新
        raw_response(str)           — 原始指令应答（调试用）
        error(str)                  — 通信异常

    回调（纯 Python，无 Qt 依赖也可用）：
        set_status_callback(fn)     — fn(CommStatus)
        set_raw_callback(fn)        — fn(str)
    """

    status_updated = Signal(object)
    raw_response = Signal(str)
    error = Signal(str)

    def __init__(self, arduino, parent=None):
        super().__init__(parent)
        self._arduino = arduino
        self._queue = queue.Queue()
        self._running = False
        self._cb_status = None
        self._cb_raw = None
        self._cb_error = None
        cfg = get_config()
        comm = cfg.get('comm', {})
        self._timeout = comm.get('timeout', 5.0)
        self._retries = comm.get('retries', 2)

    def set_status_callback(self, fn):
        self._cb_status = fn

    def set_raw_callback(self, fn):
        self._cb_raw = fn

    def set_error_callback(self, fn):
        self._cb_error = fn

    def send(self, request):
        """主线程调用：投递 CommRequest 到队列。"""
        if not isinstance(request, CommRequest):
            raise TypeError("需要 CommRequest 实例")
        self._queue.put(request)

    def stop(self):
        """通知线程退出（不阻塞）。发送队列毒丸。"""
        self._running = False
        self._queue.put(CommRequest('disconnect'))

    def run(self):
        """主循环。"""
        self._running = True
        while self._running:
            try:
                req = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if req is None or req.request_type == 'disconnect':
                break

            try:
                self._handle(req)
            except Exception as e:
                self._emit_error(f"通信处理异常：{e}")
                self._emit_status(CommStatus('error', str(e)))

    # ── 处理 ────────────────────────────────────────────

    def _handle(self, req):
        if req.request_type == 'abort':
            self._do_abort()
        elif req.request_type == 'batch_send':
            self._do_batch(req.payload)
        elif req.request_type == 'raw':
            self._do_raw(req.payload or '')

    def _do_abort(self):
        """紧急中止：清空队列 + 发送 ABORT。"""
        self._clear_queue()
        self._emit_status(CommStatus('sending', 'ABORT'))
        resp, ok = self._send_cmd('ABORT', expect='ABORT_DONE')
        if ok:
            self._emit_status(CommStatus('aborted', resp))
        else:
            self._emit_status(CommStatus('error', 'ABORT 无响应'))

    def _do_batch(self, targets):
        """发送一批目标坐标。"""
        if not targets:
            self._emit_status(CommStatus('done', '空批次，跳过'))
            return

        n = len(targets)
        self._emit_status(CommStatus('connecting', f'批次启动，{n} 个目标'))

        resp, ok = self._send_cmd(f'BATCH_START,COUNT={n}', expect='BATCH_READY')
        if not ok:
            self._emit_status(CommStatus('error', '下位机未就绪'))
            return

        success = 0
        for i, (x, y) in enumerate(targets):
            cmd = f'TARGET,SEQ={i+1},X={x:.1f},Y={y:.1f}'
            self._emit_status(CommStatus('sending', f'{i+1}/{n}'))
            resp, ok = self._send_cmd(cmd, expect='TARGET_DONE')
            if ok:
                success += 1
            else:
                self._emit_status(CommStatus('error', f'目标 {i+1} 失败'))
                break

        self._emit_status(CommStatus('waiting', '完成批次'))
        self._send_cmd(f'BATCH_COMPLETE,SUCCESS={success},TOTAL={n}',
                       expect='BATCH_FINISHED')
        self._emit_status(CommStatus('done', f'批次完成：{success}/{n}'))

    def _do_raw(self, command):
        """透传原始指令。"""
        resp = self._arduino.send_raw(command, timeout=self._timeout)
        self._emit_raw(resp or '')

    # ── 双通道通知 ──────────────────────────────────────

    def _emit_status(self, status):
        if self._cb_status:
            try:
                self._cb_status(status)
            except Exception:
                pass
        self.status_updated.emit(status)

    def _emit_raw(self, resp):
        if self._cb_raw:
            try:
                self._cb_raw(resp)
            except Exception:
                pass
        self.raw_response.emit(resp)

    def _emit_error(self, msg):
        if self._cb_error:
            try:
                self._cb_error(msg)
            except Exception:
                pass
        self.error.emit(msg)

    # ── 辅助 ────────────────────────────────────────────

    def _send_cmd(self, command, expect=None):
        """发送指令并等待应答。"""
        resp, ok = self._arduino.send_with_retry(
            command, timeout=self._timeout, retries=self._retries)
        if not ok:
            return resp, False
        if expect and expect not in resp:
            return resp, False
        return resp, True

    def _clear_queue(self):
        """清空待处理队列（中止时调用）。"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
