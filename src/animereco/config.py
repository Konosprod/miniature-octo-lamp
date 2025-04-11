import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path("../../.env"))

SCALEWAY_API_KEY = os.environ.get("SCALEWAY_API_KEY", "DEFINE ME")
SCALEWAY_API_SECRET = os.environ.get("SCALEWAY_API_SECRET", "DEFINE ME")
SCALEWAY_BASE_API = os.environ.get("SCALEWAY_BASE_API", "https://api.scaleway.ai/v1")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "DEFINE ME")
