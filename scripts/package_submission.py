from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "kaggriculture_agent"


def build(output: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_name:
        staging = Path(temp_name)
        shutil.copytree(SRC, staging / "kaggriculture_agent", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (staging / "main.py").write_text(
            "from kaggriculture_agent import kaggriculture_agent\n\n"
            "def agent(obs, configuration=None):\n"
            "    return kaggriculture_agent(obs, configuration)\n",
            encoding="utf-8",
        )
        with tarfile.open(output, "w:gz") as archive:
            archive.add(staging / "main.py", arcname="main.py")
            archive.add(staging / "kaggriculture_agent", arcname="kaggriculture_agent")

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    with tarfile.open(output, "r:gz") as archive:
        names = archive.getnames()
    if "main.py" not in names:
        raise RuntimeError("submission archive must contain main.py at its root")
    return {"path": str(output), "sha256": digest, "size_bytes": output.stat().st_size, "files": names}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "submission.tar.gz")
    args = parser.parse_args()
    metadata = build(args.output)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
