from __future__ import annotations

import os
import csv
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import re


COMPETITION = "kaggriculture"
PACKAGE = Path("dist/submission.tar.gz")
SUBMISSION_CONFIG = Path("configs/submission.json")


def run_cli(*args: str) -> str:
    result = subprocess.run(["kaggle", *args], check=True, capture_output=True, text=True)
    return result.stdout


def verify_competition_is_open() -> None:
    config = json.loads(SUBMISSION_CONFIG.read_text(encoding="utf-8"))
    if config["competition"] != COMPETITION:
        raise RuntimeError("Submission configuration names a different competition.")
    deadline_at = datetime.fromisoformat(config["deadline_utc"])
    if datetime.now(timezone.utc) >= deadline_at:
        raise RuntimeError(f"Kaggriculture submission deadline has passed: {config['deadline_utc']}")

    raw = run_cli("competitions", "list", "--search", COMPETITION, "--format", "json")
    data = json.loads(raw)
    items = data if isinstance(data, list) else data.get("data", data.get("competitions", []))
    match = next((item for item in items if item.get("ref") == COMPETITION), None)
    if not match:
        raise RuntimeError("Kaggriculture is not visible to the authenticated Kaggle account.")
    deadline = match.get("deadline")
    if deadline:
        live_deadline = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
        if live_deadline.tzinfo is None:
            live_deadline = live_deadline.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= live_deadline:
            raise RuntimeError(f"Kaggriculture submission deadline has passed: {deadline}")


def verify_submission_budget(message: str) -> None:
    config = json.loads(SUBMISSION_CONFIG.read_text(encoding="utf-8"))
    raw = run_cli("competitions", "submissions", COMPETITION, "--csv", "--quiet")
    rows = list(csv.DictReader(io.StringIO(raw))) if raw.strip() else []
    today = datetime.now(timezone.utc).date().isoformat()
    today_count = 0
    for row in rows:
        text = " ".join(str(value) for value in row.values())
        if message in text:
            raise RuntimeError("This commit is already present in the Kaggle submission history.")
        date_values = [str(value) for key, value in row.items() if "date" in key.lower()]
        if today in text or any(re.match(rf"^{re.escape(today)}", value) for value in date_values):
            today_count += 1
    if today_count >= int(config["daily_submission_limit"]):
        raise RuntimeError("The Kaggriculture daily submission limit has been reached.")


def submit(message: str) -> str:
    result = subprocess.run(
        ["kaggle", "competitions", "submit", COMPETITION, "-f", str(PACKAGE), "-m", message],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def main() -> int:
    if not os.environ.get("KAGGLE_API_TOKEN"):
        print("Submission stopped: KAGGLE_API_TOKEN is not configured.", file=sys.stderr)
        return 2
    if not PACKAGE.is_file():
        print(f"Submission stopped: package does not exist: {PACKAGE}", file=sys.stderr)
        return 2
    config = json.loads(SUBMISSION_CONFIG.read_text(encoding="utf-8"))
    if PACKAGE.stat().st_size > int(config["max_size_bytes"]):
        print("Submission stopped: package exceeds the official 100 MiB limit.", file=sys.stderr)
        return 2

    commit = os.environ.get("GITHUB_SHA", "local")[:12]
    message = f"kaggriculture-agent commit={commit}"
    try:
        verify_competition_is_open()
        verify_submission_budget(message)
        print(submit(message), end="")
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"Submission stopped safely: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
