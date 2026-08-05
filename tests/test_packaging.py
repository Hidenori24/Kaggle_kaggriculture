import tarfile

from scripts.package_submission import build


def test_submission_archive_has_root_entrypoint(tmp_path):
    metadata = build(tmp_path / "submission.tar.gz")
    assert metadata["sha256"]
    with tarfile.open(tmp_path / "submission.tar.gz", "r:gz") as archive:
        assert "main.py" in archive.getnames()
        assert "kaggriculture_agent/strategy.py" in archive.getnames()

