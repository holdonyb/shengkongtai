"""固定模型文件和下载校验清单。"""
MODELS = {
    "qwen_asr": {
        "name": "Qwen3-ASR-1.7B", "directory": "qwen3-asr-1.7b",
        "source": "models/Qwen3-ASR-1.7B",
        "files": {
            "qwen3_asr_encoder_frontend.fp16.onnx": "9f35b64d69bccc215970dd0a9d84f68d528d86826c7742d63370e67c133b20ae",
            "qwen3_asr_encoder_backend.fp16.onnx": "6949ee6aa6cc21f74f55921289db5271969aad62e141b971499ab7da3a373945",
            "qwen3_asr_llm.q4_k.gguf": "8eb99f67d9bcd882e825344e05b0e60ae77bc0b2830f972a7b4b013e91ea14a6",
        },
    },
    "fun_asr_nano": {
        "name": "Fun-ASR-Nano", "directory": "fun-asr-nano",
        "source": "models/Fun-ASR-Nano/Fun-ASR-Nano-GGUF",
        "archive_url": "https://github.com/HaujetZhao/CapsWriter-Offline/releases/download/models/Fun-ASR-Nano-GGUF.zip",
        "archive_sha256": "26a557923aedc44f1a3033d0a9b9c7b13cbb551f57fb9fd4b15a67bb4b57f998",
        "archive_size": 834231292,
        "files": {
            "Fun-ASR-Nano-Encoder-Adaptor.fp16.onnx": "ce21db255c94a25d740485c0144efc7eec496c7845ecf02df5cb3afc4c974d27",
            "Fun-ASR-Nano-CTC.fp16.onnx": "433390b8bc7b1607c09e15ef898e387770c028684a186cb80eb6a9e3a6f70f40",
            "Fun-ASR-Nano-Decoder.q5_k.gguf": "95f1ac301ff554de352fb272a442575f177c5f83ae376a9417924ece0443f4ba",
            "tokens.txt": "1c3670431c8b35557515148ad476fc0d61e33f7deb04964bdb56e35ae12e05d1",
        },
    },
}
