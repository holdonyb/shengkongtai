# Project Status

## Purpose

声控台（ShengKongTai，英文工作名 VoxPilot）：独立维护的本地语音输入与桌面语音遥控项目，衍生自 CapsWriter-Offline。首个发行版 v0.1.0 提供 Linux 听写。

## Verified Current State

- 从个人 CapsWriter 分支 `5e8a429` 的 Linux 发布白名单抽取源码，建立独立 Git 历史、模块、命令、界面名称及 XDG 数据路径。
- Linux CPU 支持 Fun-ASR-Nano 与 Qwen3-ASR-1.7B；Fun-ASR 默认使用当前上游 FP16 编码器/CTC + Q5_K 解码器，自动下载并校验；Qwen3 通过准确的 FP16/Q4_K 权重目录导入。
- 2026-09-29 已下载并校验上游完整 Fun-ASR ZIP（834,231,292 字节）和全部四个模型文件。
- 2026-09-29：19 项 Linux 边界回归通过；Fun-ASR 与 Qwen3 均完成真实模型和 Xvfb 桌面输入验证。Fun-ASR 发行包在独立且含空格的 HOME 完成安装、桌面入口、自启动、升级保留配置、故意依赖失败保留旧入口、卸载保留模型与配置。详见 `docs/VALIDATION.md`。
- 保留 MIT 版权和模型/运行库来源；源码、Release 不包含个人数据或模型权重。

## Active Work

v0.1.0 交付独立源码、Linux 程序包和可复制的 AI 安装 prompt，公开入口为 https://github.com/holdonyb/shengkongtai 。Windows Agent 和 ActivityRecorder 继续在原项目迭代，尚未迁入此版本。

## Run

`bash install-linux.sh --model fun_asr_nano`，然后 `~/.local/bin/shengkongtai`。

## Validate

`python linux/test_linux.py`；`linux/validate_install.py` 可用隔离 HOME 验证发行包，并通过 `--desktop-smoke --wav <官方夹具>` 在 Xvfb 中测试真实模型和输入。

## Known Risks

- 原生 Ubuntu/Debian 麦克风、Wayland、ARM 尚未完整验收；当前只发布 x86_64 CPU 包。
- 上游模型文件改变时固定校验会拒绝安装，需要显式验证新版本后更新清单。
- 当前没有 Windows 安装包、LLM 润色或浏览器遥控功能。

## Next Smallest Action

按 `docs/ROADMAP.md` 将已有 Windows Agent 的一个浏览器媒体任务做成可验证闭环，再迁入新项目。安装交接见 `docs/INSTALL_WITH_AI_ZH.md`。
