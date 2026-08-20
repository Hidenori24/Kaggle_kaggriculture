from __future__ import annotations

import os
import csv
import hashlib
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
    """Validate the repository's verified deadline without using list search.

    Kaggriculture is a simulation competition and may not be returned by the
    CLI's public ``competitions list --search`` endpoint even when the
    authenticated account has joined it.  The previous visibility check
    therefore stopped valid submissions before ``competitions submit`` ran.
    The configured deadline is recorded from the official competition page;
    Kaggle itself remains the authority for access and live submission state.
    """
    config = json.loads(SUBMISSION_CONFIG.read_text(encoding="utf-8"))
    if config["competition"] != COMPETITION:
        raise RuntimeError("Submission configuration names a different competition.")
    deadline_at = datetime.fromisoformat(config["deadline_utc"])
    if datetime.now(timezone.utc) >= deadline_at:
        raise RuntimeError(f"Kaggriculture submission deadline has passed: {config['deadline_utc']}")


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


def package_sha256() -> str:
    digest = hashlib.sha256()
    with PACKAGE.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lookup_submission(message: str) -> dict[str, object]:
    """Return the matching Kaggle history row without failing a submission.

    Kaggle accepts the submission before this lookup runs.  A transient CLI
    or score propagation failure must therefore be recorded as a lookup error
    rather than causing a false-negative workflow after a real submission.
    """
    raw = run_cli("competitions", "submissions", COMPETITION, "--csv", "--quiet")
    rows = list(csv.DictReader(io.StringIO(raw))) if raw.strip() else []
    matches = []
    for row in rows:
        text = " ".join(str(value) for value in row.values())
        if message in text:
            matches.append(row)
    if not matches:
        return {"lookup_status": "submitted_but_not_visible_yet"}
    row = matches[0]
    return {
        "lookup_status": "visible",
        "submission_id": row.get("ref") or row.get("id") or row.get("submissionId"),
        "public_score": row.get("publicScore") or row.get("public_score"),
        "private_score": row.get("privateScore") or row.get("private_score"),
        "history_row": row,
    }


def write_submission_record(record: dict[str, object]) -> None:
    Path("submission-result.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
    full_commit = os.environ.get("GITHUB_SHA", "local")
    message = f"kaggriculture-agent commit={commit}"
    record: dict[str, object] = {
        "competition": COMPETITION,
        "commit_sha": full_commit,
        "message": message,
        "package": str(PACKAGE),
        "package_sha256": package_sha256(),
        "package_size_bytes": PACKAGE.stat().st_size,
        "status": "not_submitted",
    }
    try:
        verify_competition_is_open()
        try:
            verify_submission_budget(message)
            record["history_preflight"] = "verified"
        except subprocess.CalledProcessError:
            # Kaggle's history endpoint can be temporarily unavailable for
            # this simulation competition. The submit endpoint is
            # authoritative, so do not skip a submission only because this
            # read failed. Duplicate and daily-limit errors remain
            # RuntimeError and still stop safely.
            record["history_preflight"] = "unavailable"
            print(
                "Submission history preflight unavailable; attempting the "
                "authoritative Kaggle submit endpoint.",
                file=sys.stderr,
            )
        output = submit(message)
        print(output, end="")
        record["status"] = "submitted"
        record["kaggle_cli_output"] = output.strip()
        try:
            record.update(lookup_submission(message))
        except (subprocess.CalledProcessError, OSError) as exc:
            record["lookup_status"] = "lookup_failed"
            record["lookup_error"] = str(exc)
        write_submission_record(record)
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        record["status"] = "stopped_safely"
        record["error"] = str(exc)
        write_submission_record(record)
        print(f"Submission stopped safely: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
