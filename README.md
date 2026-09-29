# 声控台 · ShengKongTai

本地语音输入，逐步扩展为桌面语音遥控器。英文工作名为 VoxPilot；仓库和安装命令统一使用 **shengkongtai**，避免与已有同名项目混淆。

**v0.1.0 提供 Ubuntu / Debian x86_64 离线听写**，支持 Fun-ASR-Nano 和 Qwen3-ASR-1.7B。识别使用 CPU，不需要 API Key。首次安装联网下载依赖和模型，之后可以离线使用。

## 安装

在日常桌面用户的终端执行（需要 git）：

```bash
git clone --branch v0.1.0 --depth 1 https://github.com/holdonyb/shengkongtai.git
cd shengkongtai
bash install-linux.sh --model fun_asr_nano
```

安装器自动获取 Fun-ASR 模型，校验压缩包和逐文件 SHA256。模型下载约 796 MiB，建议预留至少 4 GB 空间。仅系统依赖通过 sudo 安装，程序和虚拟环境均在用户目录。网络不便时可以导入已有模型，见 [完整安装说明](LINUX.md)。

从应用菜单打开「声控台」，或执行 `~/.local/bin/shengkongtai`。

- **X11**：点击目标输入框，按住 F8 说话，松开后自动粘贴。
- **Wayland**：点击录音按钮，或将系统快捷键绑定到 `~/.local/bin/shengkongtai toggle` 的绝对路径；一次开始，再按结束，识别后 Ctrl+V。

把 [安装 prompt](docs/INSTALL_WITH_AI_ZH.md) 交给目标 Linux 机器上的 AI，可以继续完成设备检查、安装和现场验证。

## 当前功能

| 功能 | 状态 |
| --- | --- |
| Fun-ASR / Qwen3 本地识别、模型切换 | 已实现 |
| X11 按键录音、中文粘贴、取消、窗口切换保护 | 已实现 |
| Wayland 按钮/系统快捷键录音、剪贴板输出 | 已实现，原生桌面待实测 |
| Windows 完整输入工具、LLM 润色 | 在前身项目中，尚未迁入本仓库 |
| 桌面语音遥控、操作经验学习 | 开发方向，详见 [路线图](docs/ROADMAP.md) |

应用不保存录音和听写历史。系统剪贴板和剪贴板管理器可能保存已复制的结果。配置、模型和错误日志位于用户目录；不连接 ActivityRecorder。

测试环境、功能检查与识别样本结果见 [验证记录](docs/VALIDATION.md)。

## 来源与许可

本项目从 [CapsWriter-Offline](https://github.com/HaujetZhao/CapsWriter-Offline) 及其 [个人分支](https://github.com/holdonyb/CapsWriter-Offline) 衍生，保留并复用其中的 ASR 推理代码，现以独立名称维护和发布。感谢 Haujet Zhao 及原项目贡献者。

应用代码采用 [MIT](LICENSE)。原项目版权声明和模型、运行库来源保留在 [第三方说明](linux/licenses/NOTICE.md)；模型采用各自的许可。
