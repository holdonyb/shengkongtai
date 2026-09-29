"""复用本机 Qwen3-ASR / Fun-ASR-Nano 模型与推理实现。"""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile
from .catalog import MODELS



def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified(directory: Path, model_type: str = "qwen_asr") -> bool:
    return all((directory / name).is_file() and sha256(directory / name) == digest
               for name, digest in MODELS[model_type]["files"].items())


def download_archive(destination: Path, model_type: str) -> Path:
    item = MODELS[model_type]
    request = urllib.request.Request(item["archive_url"], headers={"User-Agent": "ShengKongTai/0.1"})
    expected = item["archive_size"]
    print(f"下载 {item['name']} 模型（{expected / 1024**2:.0f} MiB），首次安装需要联网。", flush=True)
    received = 0
    next_notice = 25 * 1024**2
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            received += len(chunk)
            if received > expected:
                raise ValueError("模型下载大小与固定版本不符")
            output.write(chunk)
            if received >= next_notice:
                print(f"模型下载 {received / expected:.0%}", flush=True)
                next_notice += 25 * 1024**2
    if received != expected or sha256(destination) != item["archive_sha256"]:
        raise ValueError("模型压缩包 SHA256 或大小校验失败，请重试或导入已有模型")
    return destination


def install_model(destination: Path, source: Path | None = None, archive: Path | None = None,
                  model_type: str = "qwen_asr") -> None:
    files = MODELS[model_type]["files"]
    label = MODELS[model_type]["name"]
    if verified(destination, model_type):
        print(f"{label} 模型已就绪。", flush=True)
        return
    if source is None and archive is None and "archive_url" not in MODELS[model_type]:
        raise ValueError(f"未找到 {label} 权重。请使用含模型安装包，或加 --model-dir 指向原模型目录")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".download-", dir=destination) as temp:
        staging = Path(temp)
        if source is None and archive is None:
            archive = download_archive(staging / "model.zip", model_type)
        if source:
            if not verified(source, model_type):
                raise ValueError(f"{label} 模型 SHA256 校验失败，请使用 LINUX.md 中指定的版本")
            for name in files:
                shutil.copyfile(source / name, staging / name)
        else:
            if not zipfile.is_zipfile(archive):
                raise ValueError("模型压缩包不是有效 ZIP，无法执行 SHA256 校验")
            with zipfile.ZipFile(archive) as bundle:
                for name in files:
                    members = [m for m in bundle.infolist() if not m.is_dir() and Path(m.filename).name == name]
                    if len(members) != 1:
                        raise ValueError(f"模型压缩包缺少唯一的 {name}")
                    # 仅读取指定成员字节，不解压任意路径或链接。
                    with bundle.open(members[0]) as src, (staging / name).open("wb") as out:
                        shutil.copyfileobj(src, out)
        if not verified(staging, model_type):
            raise ValueError(f"{label} 模型文件 SHA256 校验失败")
        for name in files:
            os.replace(staging / name, destination / name)
    print(f"{label} 模型校验通过。", flush=True)


def prepare_audio(samples, sample_rate: int):
    import numpy as np
    from scipy.signal import resample_poly
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim != 1 or not 8000 <= sample_rate <= 192000:
        raise ValueError("需要单声道 8–192kHz 音频")
    if not np.all(np.isfinite(samples)):
        raise ValueError("音频中存在非法采样值")
    if sample_rate != 16000:
        divisor = math.gcd(sample_rate, 16000)
        samples = resample_poly(samples, 16000 // divisor, sample_rate // divisor).astype(np.float32)
    return np.ascontiguousarray(samples)


class Recognizer:
    def __init__(self, directory: Path, language: str = "auto", num_threads: int = 4,
                 model_type: str = "qwen_asr"):
        from .runtime import library_dir, verified_runtime
        from .config import data_dir, config_dir
        self.model_type = model_type
        for name in MODELS[model_type]["files"]:
            if not (directory / name).is_file():
                raise FileNotFoundError(f"{MODELS[model_type]['name']} 模型未安装，请重新运行含模型安装包")
        if not verified_runtime():
            raise RuntimeError("Linux llama.cpp 运行库未就绪，请重新运行安装脚本")
        os.environ["CAPSWRITER_LLAMA_LIB_DIR"] = str(library_dir())
        from util import setup_logger
        setup_logger("server", log_dir=str(data_dir() / "logs"), level="WARNING")
        if model_type == "fun_asr_nano":
            from util.fun_asr_gguf import create_asr_engine
            self.language = {"auto": None, "zh": "中文", "en": "英文", "ja": "日文"}[language]
            config_dir().mkdir(parents=True, exist_ok=True)
            self.engine = create_asr_engine(
                encoder_onnx_path=str(directory / "Fun-ASR-Nano-Encoder-Adaptor.fp16.onnx"),
                ctc_onnx_path=str(directory / "Fun-ASR-Nano-CTC.fp16.onnx"),
                decoder_gguf_path=str(directory / "Fun-ASR-Nano-Decoder.q5_k.gguf"),
                tokens_path=str(directory / "tokens.txt"), hotwords_path=str(config_dir() / "hotwords.txt"),
                dml_enable=False, vulkan_enable=False, n_threads=num_threads, verbose=False,
            )
            return
        # 保持 ONNX 先于 llama 的加载顺序，复用修过指针生命周期的共享绑定。
        from util.qwen_asr_gguf import create_asr_engine
        self.language = {"auto": None, "zh": "Chinese", "en": "English", "ja": "Japanese",
                         "ko": "Korean", "yue": "Cantonese"}[language]
        self.engine = create_asr_engine(
            model_dir=str(directory), encoder_frontend_fn="qwen3_asr_encoder_frontend.fp16.onnx",
            encoder_backend_fn="qwen3_asr_encoder_backend.fp16.onnx", llm_fn="qwen3_asr_llm.q4_k.gguf",
            use_dml=False, vulkan_enable=False, n_ctx=2048, chunk_size=80.0,
            pad_to=30, verbose=False, num_threads=num_threads,
        )

    def transcribe(self, samples, sample_rate: int) -> str:
        from util.server.text_merge import merge_by_text
        from util.tools.chinese_itn import chinese_to_num
        from util.tools.format_tools import adjust_space
        samples = prepare_audio(samples, sample_rate)
        if len(samples) < 4000:
            return ""
        if len(samples) > 16000 * 120:
            raise ValueError("单次识别最多 120 秒")
        text = ""
        offset = 0
        # 与 Windows Qwen 麦克风管线相同：15s 步长、1.5s 重叠，避免长音频截断。
        while offset < len(samples):
            remaining = len(samples) - offset
            length = int(16.5 * 16000) if remaining >= 18 * 16000 else remaining
            stream = self.engine.create_stream()
            stream.accept_waveform(16000, samples[offset:offset + length])
            options = {"verbose": False} if self.model_type == "fun_asr_nano" else {}
            self.engine.decode_stream(stream, language=self.language, **options)
            text = merge_by_text(text, stream.result.text.strip())
            if length == remaining:
                break
            offset += 15 * 16000
        return chinese_to_num(adjust_space(text)).strip()
