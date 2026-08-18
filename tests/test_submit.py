import json
import subprocess

import scripts.submit as submit_script


def _prepare_submission(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    (tmp_path / "dist").mkdir()
    (tmp_path / "configs" / "submission.json").write_text(
        json.dumps(
            {
                "competition": "kaggriculture",
                "max_size_bytes": 1000,
                "daily_submission_limit": 5,
                "deadline_utc": "2099-09-30T23:59:59+00:00",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "dist" / "submission.tar.gz").write_bytes(b"package")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(submit_script, "PACKAGE", tmp_path / "dist" / "submission.tar.gz")
    monkeypatch.setattr(submit_script, "SUBMISSION_CONFIG", tmp_path / "configs" / "submission.json")
    monkeypatch.setenv("KAGGLE_API_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)


def test_history_preflight_failure_does_not_skip_submit(tmp_path, monkeypatch):
    _prepare_submission(tmp_path, monkeypatch)
    monkeypatch.setattr(
        submit_script,
        "verify_submission_budget",
        lambda message: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, ["kaggle", "competitions", "submissions"])
        ),
    )
    submitted = []
    monkeypatch.setattr(submit_script, "submit", lambda message: submitted.append(message) or "accepted")
    monkeypatch.setattr(
        submit_script,
        "lookup_submission",
        lambda message: {"lookup_status": "visible", "submission_id": "123"},
    )

    assert submit_script.main() == 0
    assert len(submitted) == 1
    record = json.loads((tmp_path / "submission-result.json").read_text(encoding="utf-8"))
    assert record["status"] == "submitted"
    assert record["history_preflight"] == "unavailable"


def test_duplicate_or_budget_error_still_stops_safely(tmp_path, monkeypatch):
    _prepare_submission(tmp_path, monkeypatch)
    monkeypatch.setattr(
        submit_script,
        "verify_submission_budget",
        lambda message: (_ for _ in ()).throw(RuntimeError("duplicate")),
    )
    submitted = []
    monkeypatch.setattr(submit_script, "submit", lambda message: submitted.append(message) or "accepted")

    assert submit_script.main() == 2
    assert submitted == []
    record = json.loads((tmp_path / "submission-result.json").read_text(encoding="utf-8"))
    assert record["status"] == "stopped_safely"
