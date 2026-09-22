import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path("../../.env"))

SCW_SECRET_KEY = os.environ.get("SCW_SECRET_KEY", "DEFINE ME")
SCALEWAY_BASE_API = os.environ.get("SCALEWAY_BASE_API", "DEFINE ME")
