"""模拟器实现。"""

import time
from pathlib import Path
from typing import Optional, Callable

import numpy as np
import cv2
from config import get_config
from src.devices.interfaces import DeviceState, DeviceBase


class SimCamera:
    """模拟相机。"""

    def __init__(self, test_images_dir=None):
        self._state = DeviceState.DISCONNECTED
        self._images = []
        self._index = 0
        cfg = get_config()
        sim_cfg = cfg.get('simulation', {})
        camera_cfg = sim_cfg.get('camera', {})
        self._test_dir = (
            test_images_dir
            or sim_cfg.get('test_images_dir')
            or camera_cfg.get('image_dir')
            or 'test_images'
        )

    def connect(self):
        self._load_images()
        if not self._images:
            self._images.append(self._generate_demo_image())
        self._state = DeviceState.IDLE
        return True

    def disconnect(self):
        self._state = DeviceState.DISCONNECTED
        self._images.clear()

    def grab_frame(self):
        if self._state == DeviceState.DISCONNECTED:
            return None
        self._state = DeviceState.BUSY
        if not self._images:
            frame = self._generate_demo_image()
        else:
            frame = self._images[self._index % len(self._images)]
            self._index += 1
        self._state = DeviceState.IDLE
        return frame.copy()

    def set_exposure(self, exposure_ms):
        self._log(f"[SimCamera] 忽略曝光设置：{exposure_ms:.1f} ms（模拟模式）")

    def get_state(self) -> DeviceState:
        return self._state

    def get_camera_info(self):
        return {
            'name': 'SimCamera',
            'mode': 'simulation',
            'image_count': len(self._images),
            'test_dir': self._test_dir,
        }

    def _load_images(self):
        self._images.clear()
        path = Path(self._test_dir)
        if not path.exists():
            return
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.bmp'):
            for f in path.glob(ext):
                img = cv2.imread(str(f))
                if img is not None:
                    self._images.append(img)

    @staticmethod
    def _generate_demo_image() -> np.ndarray:
        """生成演示图。"""
        img = np.full((512, 512, 3), 60, dtype=np.uint8)
        cv2.circle(img, (200, 200), 30, (0, 200, 200), -1)
        cv2.circle(img, (350, 300), 20, (0, 180, 220), -1)
        cv2.circle(img, (150, 400), 25, (0, 210, 190), -1)

        noise_level = get_config().get('simulation', {}).get('noise_level', 0.0)
        if noise_level > 0:
            noise = np.random.normal(0, noise_level * 255, img.shape).astype(np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return img


class SimArduino(DeviceBase):
    """模拟 Arduino。"""

    def __init__(self, message_callback: Optional[Callable[[str], None]] = None):
        super().__init__(message_callback)
        self._state = DeviceState.DISCONNECTED
        self._pos   = [0.0, 0.0, 0.0]   # [X, Y, Z]
        cfg = get_config()
        sim_cfg = cfg.get('simulation', {})
        arduino_cfg = sim_cfg.get('arduino', {})
        self._move_delay = sim_cfg.get('arduino_move_delay', arduino_cfg.get('move_delay', 0.3))

    def connect(self):
        self._state = DeviceState.IDLE
        self._log("[SimArduino] 虚拟串口已连接（模拟模式）")
        self._log(f"   当前虚拟位置：X={self._pos[0]:.1f}  "
                  f"Y={self._pos[1]:.1f}  Z={self._pos[2]:.1f}")
        return True

    def disconnect(self):
        self._blast_active = False
        self._state = DeviceState.DISCONNECTED
        self._log("[SimArduino] 虚拟串口已断开")

    def move_absolute(self, x, y, z=0.0):
        self._state = DeviceState.BUSY
        self._log(f"[SimArduino] G0 X={x:.1f} Y={y:.1f} Z={z:.1f}")
        time.sleep(self._move_delay)
        self._pos = [x, y, z]
        self._state = DeviceState.IDLE
        self._log(f"   虚拟电机运动完成，当前位置："
                  f"X={self._pos[0]:.1f}  Y={self._pos[1]:.1f}  Z={self._pos[2]:.1f}")
        return True

    def move_relative(self, dx, dy, dz=0.0):
        return self.move_absolute(
            self._pos[0] + dx,
            self._pos[1] + dy,
            self._pos[2] + dz,
        )

    def get_position(self):
        if self._state == DeviceState.DISCONNECTED:
            return None
        return {
            'x': self._pos[0],
            'y': self._pos[1],
            'z': self._pos[2],
            'timestamp': time.time(),
        }

    def stop_motors(self):
        self._blast_active = False
        self._state = DeviceState.IDLE
        self._log("[SimArduino] 电机紧急停止")

    def reset(self):
        self._blast_active = False
        self._pos = [0.0, 0.0, 0.0]
        self._state = DeviceState.IDLE
        self._log("[SimArduino] 控制器已重置，位置归零")

    def get_state(self) -> DeviceState:
        return self._state

    def send_raw(self, command, timeout=5):
        """模拟指令收发。"""
        cmd = command.strip().upper()
        self._log(f"[SimArduino] 收到指令：{command.strip()}")

        if cmd.startswith('G0') or cmd.startswith('G1'):
            parts = cmd.split()
            x, y, z = self._pos[0], self._pos[1], self._pos[2]
            for p in parts[1:]:
                if p.startswith('X'):
                    x = float(p[1:])
                elif p.startswith('Y'):
                    y = float(p[1:])
                elif p.startswith('Z'):
                    z = float(p[1:])
            self.move_absolute(x, y, z)
            return f"OK X={self._pos[0]:.1f} Y={self._pos[1]:.1f} Z={self._pos[2]:.1f}"

        elif cmd.startswith('BLAST'):
            parts = command.strip().split()
            if len(parts) >= 2 and parts[1].upper() == 'ON':
                duration = float(parts[2]) if len(parts) >= 3 else 200
                self.blast_on(duration)
                return f"OK BLAST ON {duration}ms"
            elif len(parts) >= 2 and parts[1].upper() == 'OFF':
                self.blast_off()
                return "OK BLAST OFF"
            else:
                return "ERR invalid BLAST command"

        elif cmd.startswith('BATCH_START'):
            self._log(f"   模拟：准备接收批次")
            time.sleep(0.1)
            return "BATCH_READY"

        elif cmd.startswith('TARGET,'):
            parts = command.strip().split(',')
            seq = '?'
            for p in parts:
                if p.upper().startswith('SEQ='):
                    seq = p.split('=')[1]
            self._pos[0] = 0
            self._pos[1] = 0
            time.sleep(0.3)
            return f"TARGET_DONE,SEQ={seq}"

        elif cmd.startswith('BATCH_COMPLETE'):
            self._pos = [0.0, 0.0, 0.0]
            time.sleep(0.2)
            self._log(f"   模拟：批次完成，归零")
            return "BATCH_FINISHED"

        elif cmd == 'ABORT':
            self._blast_active = False
            self._pos = [0.0, 0.0, 0.0]
            self._state = DeviceState.IDLE
            self._log(f"   模拟：紧急中止，已归零")
            return "ABORT_DONE"

        elif cmd == '?':
            pos = self.get_position()
            return f"X={pos['x']:.1f} Y={pos['y']:.1f} Z={pos['z']:.1f}"

        elif cmd == 'STOP':
            self.stop_motors()
            return "OK STOPPED"

        elif cmd == 'RESET':
            self.reset()
            return "OK RESET"

        else:
            self._log(f"   未知指令：{command.strip()}")
            return f"ERR unknown command: {command.strip()}"

    def send_with_retry(self, command, timeout=5, retries=2):
        """模拟版 send_with_retry —— 与 RealArduino 签名一致。"""
        resp = self.send_raw(command, timeout=timeout)
        if resp:
            return resp, True
        return "", False

    def blast_on(self, duration_ms=None):
        if duration_ms is None:
            duration_ms = 200
        self._blast_active = True
        self._log(f"[SimArduino] 电磁阀打开（模拟喷气 {duration_ms:.0f}ms）")
        time.sleep(duration_ms / 1000.0)
        self._blast_active = False
        self._log(f"   喷气完成")
        return True

    def blast_off(self):
        self._blast_active = False
        self._log(f"[SimArduino] 电磁阀关闭")
