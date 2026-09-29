# Linux 安装与使用

声控台 v0.1.0 支持 x86_64 Ubuntu / Debian 桌面，Python 3.10+。已在 Ubuntu 24.04 / WSL2 验证；原生 Debian 和真实麦克风需目标机测试。当前使用 CPU，ARM 运行库尚未提供。

## 自动安装 Fun-ASR

```bash
git clone --branch v0.1.0 --depth 1 https://github.com/holdonyb/shengkongtai.git
cd shengkongtai
bash install-linux.sh --model fun_asr_nano
```

需要 git；如未安装，可运行 `sudo apt-get install git`。也可从 GitHub Release 下载 `ShengKongTai-0.1.0.tar.gz` 及其 `.sha256`，执行 `sha256sum -c ShengKongTai-0.1.0.tar.gz.sha256` 后解压，在 `ShengKongTai-Linux` 中运行安装脚本。

请使用普通桌面用户，只在脚本安装系统依赖时输入 sudo 密码。程序、自带 Python 虚拟环境和模型均存放在用户目录。默认选择 Fun-ASR-Nano（FP16 编码器/CTC + Q5_K 解码器）；安装器自动下载上游 796 MiB 模型包和约 23 MiB llama.cpp 运行库。检查压缩包、模型文件和运行库的固定 SHA256 后才安装。建议预留至少 4 GB 空间。

首次安装需要联网，识别过程可离线。下载失败可重试，或者使用已有权重：

```bash
bash install-linux.sh --model fun_asr_nano --model-dir /path/to/Fun-ASR-Nano-GGUF
# 也支持上游原 ZIP：
bash install-linux.sh --model fun_asr_nano --model-archive /path/to/Fun-ASR-Nano-GGUF.zip
```

如有配套运行库，可加 `--runtime-archive /path/to/llama-b7798-bin-ubuntu-x64.tar.gz`。系统依赖已齐全时可加 `--skip-system-deps`。Python 依赖使用 pip 标准镜像和离线 wheel 配置。

本仓库与程序 Release 不包含模型权重。自动下载使用 [上游模型发布页](https://github.com/HaujetZhao/CapsWriter-Offline/releases/tag/models)，准确文件与校验值见 `shengkongtai/catalog.py`。

## 使用 Qwen3-ASR

Qwen3 使用 FP16 编码器和 Q4_K 解码器，导入已有的准确权重目录：

```bash
bash install-linux.sh --model qwen_asr --model-dir /path/to/Qwen3-ASR-1.7B
```

目录中须有 `qwen3_asr_encoder_frontend.fp16.onnx`、`qwen3_asr_encoder_backend.fp16.onnx`、`qwen3_asr_llm.q4_k.gguf`。建议预留 8 GB 空间。上游 `Qwen3-ASR-1.7B-q4_k.zip` 的编码器是 INT4，不能替代本配置的 FP16 文件。

原 CapsWriter 的 Qwen3 完整包仍可作为 Qwen3 模型来源，包内运行库也可复用。声控台的 Fun-ASR 使用当前上游 FP16 编码器；此前本地 INT4 Fun-ASR 包不匹配此版本，请自动下载或导入新的 FP16 权重。两个应用有各自独立的配置和启动命令。

## 启动与切换

安装完成后，从应用菜单打开 **声控台**，或执行：

```bash
~/.local/bin/shengkongtai
~/.local/bin/shengkongtai model                 # 查看选择和已安装模型
~/.local/bin/shengkongtai model fun_asr_nano     # 选择 Fun-ASR
~/.local/bin/shengkongtai model qwen_asr         # 选择已导入的 Qwen3
~/.local/bin/shengkongtai autostart on          # 登录启动，off 关闭
```

模型切换后退出并重开窗口。默认只加载所选模型；窗口显示实际模型名称。Fun-ASR 热词放在 `~/.config/shengkongtai/hotwords.txt`，一行一个。

| 桌面 | 操作 |
| --- | --- |
| X11 / Xorg | 点击输入框，按住 F8 说话，松开识别并自动粘贴；Esc 取消。识别时切换窗口会只复制结果。 |
| Wayland | 使用录音按钮，或将系统 F8 快捷键绑定到当前用户完整路径下的 `.local/bin/shengkongtai toggle`。按一次开始，再按结束；结果手动 Ctrl+V，终端 Ctrl+Shift+V。 |

按钮录音只复制结果。默认单次最多 60 秒，可配置至 120 秒。结果可编辑、复制；应用会替换剪贴板内容。应用不保存录音或听写历史，系统剪贴板管理器可能保留复制内容。

X11 的 F8 不拦截目标应用自身的 F8 功能；冲突时修改配置中的 `hotkey`。Wayland 窗口需要 XWayland，当前不提供原生全局长按和自动粘贴。

## 检查、配置和升级

```bash
~/.local/bin/shengkongtai doctor
~/.local/bin/shengkongtai devices
~/.local/bin/shengkongtai transcribe sample.wav
~/.local/bin/shengkongtai cancel
~/.local/bin/shengkongtai quit
```

`doctor` 检查依赖、模型校验、麦克风和桌面，缺项时返回非零。WAV 转写支持最长 120 秒的 PCM16 音频，自动重采样。文件转写成功后仍应实际试一次麦克风录音。

配置位于 `~/.config/shengkongtai/config.json`，修改后重启。`input_device` 可填设备编号、名称或 null；`num_threads` 默认为 4。模型、运行库、日志和版本目录位于 `~/.local/share/shengkongtai/`，支持 XDG 环境变量。

再次运行安装器可升级；旧配置和模型保留，新依赖安装失败时保留旧启动入口。卸载：

```bash
bash install-linux.sh --uninstall
```

卸载移除程序版本、桌面入口和自启动，保留模型、运行库及配置。

## 开发验证

```bash
python3 linux/test_linux.py
xvfb-run -a python3 linux/smoke_test.py --model fun_asr_nano --wav /path/to/zh.wav
python3 linux/build_release.py
python3 linux/validate_install.py --release release/ShengKongTai-0.1.0.tar.gz --model-dir /path/to/Fun-ASR-Nano-GGUF --runtime-archive /path/to/llama-b7798-bin-ubuntu-x64.tar.gz --wav /path/to/zh.wav
```

桌面与安装测试需 xvfb、openbox、scrot、desktop-file-utils。真实模型的虚拟桌面验证包括 F8、中文粘贴、48kHz 重采样、取消和焦点保护；原生桌面麦克风与 Wayland 要在目标机补测。

当前发行包是 Linux 听写。前身 Windows 的 LLM 润色、边说边显示、完整热词纠错及语音 Agent 尚未迁入。第三方来源及许可见 `linux/licenses/NOTICE.md`。
