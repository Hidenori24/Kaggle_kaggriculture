from __future__ import annotations

import os
import sys


def main() -> int:
    if os.environ.get("KAGGRICULTURE_SUBMISSION_FORMAT_CONFIRMED") != "1":
        print("Submission stopped: official Kaggriculture submission format is not confirmed.", file=sys.stderr)
        return 2
    if not os.environ.get("KAGGLE_API_TOKEN"):
        print("Submission stopped: KAGGLE_API_TOKEN is not configured.", file=sys.stderr)
        return 2
    print("Submission adapter is intentionally disabled until the official format is recorded.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
