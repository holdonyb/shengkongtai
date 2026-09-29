# 声控台开发约定

- 独立产品，当前可安装版本为 x86_64 Linux 离线听写。Windows 语音 Agent 尚未迁入。
- Python 模块和命令为 `shengkongtai`；按 XDG 保存用户数据，与 CapsWriter 分开。
- `util/` 保留来自 CapsWriter-Offline 的共享推理代码，修改时保留版权和来源。
- 发布只用 `linux/build_release.py` 的文件白名单；个人配置、热词、录音、ActivityRecorder 数据不进 Git。
- 用项目虚拟环境验证。Linux 回归：`python linux/test_linux.py`；真实模型桌面验证使用 `xvfb-run -a python linux/smoke_test.py --model fun_asr_nano --wav <夹具>`。
- 原生麦克风、Wayland 和 Windows 证据分别记录，不以虚拟桌面替代实机结果。
- 模型下载须同时检查压缩包和模型文件 SHA256；不要改名冒充另一精度。
