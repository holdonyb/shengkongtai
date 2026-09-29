# 给 Linux 机器上的 AI 的安装 prompt

复制下面整段，在目标 Linux 桌面上的 AI 编程助手中执行：

```text
请直接帮我在这台 Ubuntu / Debian 桌面上安装「声控台 ShengKongTai」，完成后验证到可以录音输入。

项目：https://github.com/holdonyb/shengkongtai
固定版本：v0.1.0。先阅读该版本 README.md、LINUX.md 和 AGENTS.md。
这是离线语音输入工具，默认使用 Fun-ASR-Nano，也支持 Qwen3-ASR-1.7B；不要替换成 SenseVoice。

1. 检查发行版、CPU 架构、Python、空余磁盘、X11/Wayland 会话和音频输入设备。
   当前支持 x86_64、Python 3.10+，建议至少 4 GB 安装空间。若是 ARM 或没有图形桌面，明确告诉我缺少的条件。

2. 在普通桌面用户目录建立专用安装目录，clone 仓库并 checkout v0.1.0。
   已有同名目录时先检查内容，保留用户改动。安装命令：
   bash install-linux.sh --model fun_asr_nano
   脚本会通过 sudo 安装系统依赖，在用户目录建立独立 Python 环境，并自动下载固定版本的 Fun-ASR 模型和运行库。
   不要 sudo 整个安装脚本。需要密码时让用户在终端输入；不要索要或记录密码。

3. 下载失败时保留诊断信息，检查连接后重试。可以通过 --model-dir 导入已有模型目录，
   或 --model-archive 导入上游 Fun-ASR-Nano-GGUF.zip，通过 --runtime-archive 导入 llama-b7798-bin-ubuntu-x64.tar.gz。
   校验必须通过；不要关闭 SHA256 检查，也不要重命名不同精度的权重来冒充。

4. 运行 ~/.local/bin/shengkongtai doctor 和 ~/.local/bin/shengkongtai devices，修复实际检测到的问题。
   打开应用，确认显示 Fun-ASR-Nano 并且模型加载完成。选择正确麦克风。
   X11：用空白测试编辑框验证按住 F8 录音、松开识别、中文自动粘贴，以及 Esc 取消。
   Wayland：使用录音按钮，或者在系统快捷键里把 F8 绑定到当前用户的完整路径 ~/.local/bin/shengkongtai toggle；
   按一次开始，再按结束，识别后 Ctrl+V，终端 Ctrl+Shift+V。
   只在明确的测试输入框验证，保留用户剪贴板原内容供恢复。

5. 如果我选择 Qwen3，请导入符合 catalog.py 的 FP16 编码器和 Q4_K 解码器：
   bash install-linux.sh --model qwen_asr --model-dir /实际路径/Qwen3-ASR-1.7B
   上游 Qwen3-ASR-1.7B-q4_k.zip 的编码器是 INT4，不能用于这里的 FP16 配置。
   模型选择命令是 ~/.local/bin/shengkongtai model qwen_asr，切换后退出并重新打开应用。

6. 如需登录启动，用 ~/.local/bin/shengkongtai autostart on。
   卸载用 bash install-linux.sh --uninstall，配置和模型会保留。

最后告诉我：安装版本、所选模型、桌面类型、启动入口、实际通过的检查和使用方法。
如果你无法访问麦克风或桌面，就完成可做的安装并给出具体剩余操作，不能把音频文件转写算作真实麦克风验证。
此版本先提供 Linux 听写，桌面 Agent 和语音遥控不在这个发行包中。
```
