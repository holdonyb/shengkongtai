# Third-party notices

- ShengKongTai / 声控台 (working English name: VoxPilot): https://github.com/holdonyb/shengkongtai — MIT; see the root LICENSE.
- This is a derivative project, initially extracted from holdonyb/CapsWriter-Offline commit 5e8a429453723a273282c143dc6b0f2c1acc0cf9. The Linux application has its own name and data paths; shared inference code retains its upstream attribution. It is independently maintained and is not an official CapsWriter release.
- CapsWriter-Offline: https://github.com/HaujetZhao/CapsWriter-Offline — MIT; see CapsWriter-MIT.txt.
- Fun-ASR-GGUF: https://github.com/HaujetZhao/Fun-ASR-GGUF — MIT; see Fun-ASR-GGUF-MIT.txt. Inference implementation included through CapsWriter-Offline.
- Qwen3-ASR-1.7B: https://huggingface.co/Qwen/Qwen3-ASR-1.7B — Apache-2.0.
- Fun-ASR-Nano-2512: https://huggingface.co/FunAudioLLM/Fun-ASR-Nano-2512 — Apache-2.0.
- Model files are ONNX/GGUF exports and quantizations, not the original framework checkpoints. Exact filenames and hashes are in shengkongtai/catalog.py. The Qwen encoder uses FP16 and its decoder Q4_K; Fun-ASR encoder/CTC use FP16 and its decoder Q5_K. See Models-Apache-2.0.txt. The source package contains no weights; Fun-ASR can be downloaded from the attributed upstream release.
- llama.cpp b7798: https://github.com/ggml-org/llama.cpp/releases/tag/b7798 — MIT; the runtime archive retains its LICENSE, also installed beside the libraries.
- Python dependencies are installed separately by pip and retain their own package licenses.
