"""
配置加载器。
从 app_settings.yaml 和 device_params.yaml 读取配置，合并为单一字典。
"""

import yaml
from pathlib import Path


_CONFIG_DIR = Path(__file__).parent
_APP_SETTINGS = _CONFIG_DIR / 'app_settings.yaml'
_DEVICE_PARAMS = _CONFIG_DIR / 'device_params.yaml'

_config = {}


def load_config():
    """加载并合并 app_settings.yaml 和 device_params.yaml。"""
    global _config

    if _APP_SETTINGS.exists():
        with open(_APP_SETTINGS, 'r', encoding='utf-8') as f:
            app_cfg = yaml.safe_load(f)
        if not isinstance(app_cfg, dict):
            print(f"[config] 警告：配置文件 {_APP_SETTINGS} 格式不正确（预期为字典），已忽略")
    else:
        app_cfg = {}
        print(f"[config] 警告：配置文件不存在 {_APP_SETTINGS}")

    if _DEVICE_PARAMS.exists():
        with open(_DEVICE_PARAMS, 'r', encoding='utf-8') as f:
            dev_cfg = yaml.safe_load(f)
        if not isinstance(dev_cfg, dict):
            print(f"[config] 警告：配置文件 {_DEVICE_PARAMS} 格式不正确（预期为字典），已忽略")
    else:
        dev_cfg = {}
        print(f"[config] 警告：配置文件不存在 {_DEVICE_PARAMS}")

    _config = {
        'mode': app_cfg.get('mode', 'sim'),
        'pixel_per_mm': app_cfg.get('pixel_per_mm', 4.40),
        'detection': app_cfg.get('detection', {}),
        'hsv_filter': app_cfg.get('hsv_filter', {}),
        'preview_fps': app_cfg.get('preview_fps', 15),
        'detect_fps': app_cfg.get('detect_fps', 0),
        'comm': app_cfg.get('comm', {}),
        'writer': app_cfg.get('writer', {}),
        'logging': app_cfg.get('logging', {}),
        'calibration': app_cfg.get('calibration', {}),
        'simulation': app_cfg.get('simulation', {}),
        'serial': dev_cfg.get('serial', {}),
        'camera': dev_cfg.get('camera', {}),
        'motor': dev_cfg.get('motor', {}),
    }

    return _config


def get_config():
    if not _config:
        load_config()
    return _config


def get_mode():
    return get_config().get('mode', 'sim')


def set_mode(mode):
    global _config
    if mode not in ('sim', 'real'):
        raise ValueError(f"无效的模式 '{mode}'，请使用 'sim' 或 'real'")
    if not _config:
        load_config()
    _config['mode'] = mode
    print(f"[config] 模式已切换为：{mode}")


def save_config():
    """将当前内存配置写回 app_settings.yaml 和 device_params.yaml。"""
    global _config

    if not _config:
        load_config()

    app_cfg = {
        'mode': _config.get('mode', 'sim'),
        'pixel_per_mm': _config.get('pixel_per_mm', 4.40),
        'detection': _config.get('detection', {}),
        'hsv_filter': _config.get('hsv_filter', {}),
        'preview_fps': _config.get('preview_fps', 15),
        'detect_fps': _config.get('detect_fps', 0),
        'comm': _config.get('comm', {}),
        'writer': _config.get('writer', {}),
        'logging': _config.get('logging', {}),
        'calibration': _config.get('calibration', {}),
        'simulation': _config.get('simulation', {}),
    }
    dev_cfg = {
        'camera': _config.get('camera', {}),
        'serial': _config.get('serial', {}),
        'motor': _config.get('motor', {}),
    }

    try:
        with open(_APP_SETTINGS, 'w', encoding='utf-8') as f:
            yaml.safe_dump(app_cfg, f, allow_unicode=True, sort_keys=False)
        with open(_DEVICE_PARAMS, 'w', encoding='utf-8') as f:
            yaml.safe_dump(dev_cfg, f, allow_unicode=True, sort_keys=False)
        return True
    except Exception as e:
        print(f"[config] 保存配置失败：{e}")
        return False


load_config()
