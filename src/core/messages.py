"""跨线程消息定义 —— 全项目唯一数据契约。

相机线程、检测 Worker、通信线程、Writer 线程之间通过信号/队列传递
这些对象，不暴露原始 ndarray 或裸字典，避免跨线程数据竞态。
"""

from collections import namedtuple


FrameMessage = namedtuple('FrameMessage', ['qimage', 'timestamp'])
"""相机线程 -> UI：预览帧。
qimage: QImage（相机线程内已做 BGR->RGB 转换 + 降采样，直接贴 QLabel）
timestamp: 帧时间戳（time.time()）
"""


DetectionResult = namedtuple('DetectionResult', [
    'circles_pixel',      # [(x, y, r), ...] 像素坐标
    'circles_mm',          # [(x_mm, y_mm), ...] 毫米坐标
    'annotated_qimage',    # QImage 标注图（检测 Worker 内完成绘制）
    'image_bgr',           # np.ndarray 原始 BGR 帧（供 Writer 异步存盘），可为 None
])
"""检测 Worker -> 主线程：单次检测产出。

circles_pixel / circles_mm 长度一致，一一对应。
annotated_qimage 用于 UI 定格显示（红圈标注非黄目标）。
"""


class CommStatus:
    """通信线程 -> UI：状态更新。

    phase:
        'connecting'   - 正在建立连接
        'sending'      - 正在发送指令
        'waiting'      - 等待下位机应答
        'done'         - 批次处理完成
        'error'        - 通信异常（超时/断线）
        'aborted'      - 已发送 ABORT 并收到确认
    """

    def __init__(self, phase, detail=''):
        self.phase = phase
        self.detail = detail


class CommRequest:
    """主线程 -> 通信线程：发送请求。

    request_type:
        'batch_send'   - 发送一批目标坐标，payload = [(x_mm, y_mm), ...]
        'raw'          - 透传原始指令，payload = str
        'abort'        - 紧急中止，payload 忽略
        'disconnect'   - 断开连接，payload 忽略
    """

    def __init__(self, request_type, payload=None):
        self.request_type = request_type
        self.payload = payload


class WriterTask:
    """主线程 -> Writer 线程：写盘任务。

    task_type:
        'image'   - 存图，data = (ndarray, filepath)
        'json'    - 存 JSON，data = (dict, filepath)
        'shutdown' - 优雅退出毒丸，data 忽略
    """

    def __init__(self, task_type, data=None):
        self.task_type = task_type
        self.data = data
