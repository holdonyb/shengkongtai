"""仅打包明确列出的 Linux 源文件，绝不带入个人热词、密钥或录音。"""
from pathlib import Path
import argparse
import tarfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shengkongtai.package_files import SHARED_FILES
from shengkongtai.catalog import MODELS
from shengkongtai.model import verified, sha256
from shengkongtai.runtime import RUNTIME_SHA256


def build(destination=None, with_models=False, runtime_archive=None, model_types=None, model_root=None):
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("linux_version", ROOT / "shengkongtai/__init__.py")
    version = module_from_spec(spec)
    spec.loader.exec_module(version)
    selected = list(MODELS) if with_models else list(model_types or [])
    source_root = Path(model_root) if model_root else ROOT
    suffix = ("-with-models" if len(selected) > 1 else "-" + MODELS[selected[0]]["directory"]) if selected else ""
    output = Path(destination) if destination else ROOT / "release" / f"ShengKongTai-{version.__version__}{suffix}.tar.gz"
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [ROOT / name for name in ("install-linux.sh", "requirements-linux.txt", "LINUX.md", "README.md", "LICENSE", "docs/INSTALL_WITH_AI_ZH.md", "docs/ROADMAP.md", "docs/VALIDATION.md")]
    files += sorted((ROOT / "shengkongtai").glob("*.py"))
    files += [ROOT / "linux/install.py"]
    files += sorted((ROOT / "linux/licenses").glob("*"))
    files += [ROOT / name for name in SHARED_FILES]
    entries = [(path, path.relative_to(ROOT).as_posix()) for path in files]
    if selected:
        for key in selected:
            item = MODELS[key]
            source = source_root / item["source"]
            if not verified(source, key):
                raise ValueError(f"模型校验失败: {source}")
            entries += [(source / name, item["source"] + "/" + name) for name in item["files"]]
        if runtime_archive is None or sha256(Path(runtime_archive)) != RUNTIME_SHA256:
            raise ValueError("含模型包需要校验通过的 --runtime-archive")
    with tarfile.open(output, "w:gz", compresslevel=1) as archive:
        for path, name in entries:
            info = archive.gettarinfo(str(path), arcname="ShengKongTai-Linux/" + name)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mode = 0o755 if path.suffix == ".sh" else 0o644
            with path.open("rb") as stream:
                archive.addfile(info, stream)
        if selected:
            archive.add(runtime_archive, arcname="ShengKongTai-Linux/runtime/llama-b7798-bin-ubuntu-x64.tar.gz")
    digest = sha256(output)
    output.with_suffix(output.suffix + ".sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-models", action="store_true")
    parser.add_argument("--runtime-archive", type=Path)
    parser.add_argument("--model", choices=tuple(MODELS), action="append", help="只打包指定模型，可重复")
    parser.add_argument("--model-root", type=Path, help="含 models/ 的原仓库目录")
    args = parser.parse_args()
    build(with_models=args.with_models, runtime_archive=args.runtime_archive,
          model_types=args.model, model_root=args.model_root)
