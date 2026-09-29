"""XDG 路径和用户配置；与 Windows 的配置、密钥、录音完全分开。"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from .catalog import MODELS


def xdg_path(variable: str, fallback: str) -> Path:
    value = os.environ.get(variable, "")
    return Path(value) if value and Path(value).is_absolute() else Path.home() / fallback


def data_dir() -> Path:
    return xdg_path("XDG_DATA_HOME", ".local/share") / "shengkongtai"


def config_dir() -> Path:
    return xdg_path("XDG_CONFIG_HOME", ".config") / "shengkongtai"


def runtime_dir() -> Path:
    # 不使用全局 /tmp，套接字和锁仅对当前用户可见。
    root = xdg_path("XDG_RUNTIME_DIR", ".cache") / "shengkongtai"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    return root


DEFAULTS = {
    "model_type": "fun_asr_nano",
    "hotkey": "f8",
    "language": "auto",
    "num_threads": 4,
    "input_device": None,
    "auto_paste": True,
    "max_record_seconds": 60,
    "model_dir": "",
}


def load_config() -> dict:
    path = config_dir() / "config.json"
    result = DEFAULTS.copy()
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("config.json 必须是 JSON 对象")
        result.update({k: v for k, v in value.items() if k in DEFAULTS})
    if result["model_type"] not in MODELS:
        raise ValueError("model_type 请设置为 qwen_asr 或 fun_asr_nano")
    if result["model_type"] == "fun_asr_nano" and result["language"] not in {"auto", "zh", "en", "ja"}:
        raise ValueError("此 Fun-ASR-Nano 权重支持 auto/zh/en/ja；粤语请使用 auto，韩语请选择 Qwen3")
    if result["hotkey"] not in {f"f{i}" for i in range(1, 13)}:
        raise ValueError("hotkey 请设置为 f1 至 f12 中的一个键")
    if result["language"] not in {"auto", "zh", "en", "ja", "ko", "yue"}:
        raise ValueError("language 请设置为 auto/zh/en/ja/ko/yue")
    if type(result["num_threads"]) is not int or not 1 <= result["num_threads"] <= 32:
        raise ValueError("num_threads 必须是 1 至 32 的整数")
    if type(result["max_record_seconds"]) is not int or not 1 <= result["max_record_seconds"] <= 120:
        raise ValueError("max_record_seconds 必须是 1 至 120 的整数")
    if type(result["auto_paste"]) is not bool:
        raise ValueError("auto_paste 必须是 true 或 false")
    if not isinstance(result["model_dir"], str):
        raise ValueError("model_dir 必须是路径字符串")
    device = result["input_device"]
    if device is not None and (isinstance(device, bool) or not isinstance(device, (str, int))):
        raise ValueError("input_device 必须是设备编号、名称或 null")
    return result


def model_dir(config: dict) -> Path:
    return Path(config["model_dir"]).expanduser() if config["model_dir"] else data_dir() / "models" / MODELS[config["model_type"]]["directory"]


def save_model_selection(model_type: str) -> None:
    path = config_dir() / "config.json"
    value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    value.update(model_type=model_type, model_dir="")
    if model_type == "fun_asr_nano" and value.get("language") in {"ko", "yue"}:
        value["language"] = "auto"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write("\n")
    os.replace(out.name, path)


def initialize_config() -> None:
    config_dir().mkdir(parents=True, exist_ok=True, mode=0o700)
    path = config_dir() / "config.json"
    try:
        with path.open("x", encoding="utf-8") as out:
            json.dump(DEFAULTS, out, ensure_ascii=False, indent=2)
            out.write("\n")
    except FileExistsError:
        pass
