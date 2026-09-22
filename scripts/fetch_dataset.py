"""Fetch the AniList anime dataset from Kaggle into src/animereco/data/anime.pkl.

Source: https://www.kaggle.com/datasets/calebmwelsh/anilist-anime-dataset
No Kaggle API credentials needed: the /api/v1/datasets/download endpoint
redirects to a public, time-limited signed download URL for this dataset.
"""

import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

DATASET_URL = "https://www.kaggle.com/api/v1/datasets/download/calebmwelsh/anilist-anime-dataset"
PKL_NAME_IN_ZIP = "anilist_anime_data_complete.pkl"
TARGET = Path(__file__).resolve().parent.parent / "src" / "animereco" / "data" / "anime.pkl"


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading dataset from {DATASET_URL} ...")
    response = requests.get(DATASET_URL, stream=True, timeout=60)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp_zip:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            tmp_zip.write(chunk)
        tmp_zip.flush()

        print(f"Extracting {PKL_NAME_IN_ZIP} ...")
        with (
            zipfile.ZipFile(tmp_zip.name) as archive,
            archive.open(PKL_NAME_IN_ZIP) as src,
            open(TARGET, "wb") as dst,
        ):
            shutil.copyfileobj(src, dst)

    print(f"Saved to {TARGET} ({TARGET.stat().st_size / 1_000_000:.1f} MB)")


if __name__ == "__main__":
    main()
