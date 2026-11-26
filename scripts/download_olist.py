"""Download the real Olist Brazilian E-Commerce dataset into data/raw.

One-time setup:
    1. Create a free Kaggle account -> Settings -> "Create New Token"
       (saves kaggle.json to ~/.kaggle/ or set KAGGLE_USERNAME / KAGGLE_KEY).
    2. pip install kagglehub
    3. python scripts/download_olist.py

Dataset: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
(Please review the dataset's licence on Kaggle before redistributing it;
the repo keeps data/ out of Git on purpose.)
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

DATASET = "olistbr/brazilian-ecommerce"
DEST = Path("data/raw")
EXPECTED = 9


def main() -> int:
    try:
        import kagglehub
    except ImportError:
        print("Install kagglehub first:  pip install kagglehub")
        return 1

    DEST.mkdir(parents=True, exist_ok=True)
    src = Path(kagglehub.dataset_download(DATASET))
    csvs = sorted(src.rglob("*.csv"))
    for f in csvs:
        shutil.copy2(f, DEST / f.name)
        print(f"copied {f.name}")
    if len(csvs) < EXPECTED:
        print(f"Warning: expected {EXPECTED} CSV files, found {len(csvs)}.")
        return 1
    print(f"\nDone. {len(csvs)} files in {DEST.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
