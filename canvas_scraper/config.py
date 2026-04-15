"""Load configuration from .env file and environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    canvas_api_token: str
    canvas_base_url: str
    credentials_dir: Path


def load_config() -> Config:
    load_dotenv()

    token = os.getenv("CANVAS_API_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "CANVAS_API_TOKEN is not set. "
            "Copy .env.example to .env and fill in your Canvas API token.\n"
            "Generate one at: Canvas > Account > Settings > Approved Integrations"
        )

    base_url = os.getenv("CANVAS_BASE_URL", "https://canvas.uw.edu").rstrip("/")
    credentials_dir = Path(os.getenv("CREDENTIALS_DIR", "./credentials")).resolve()

    return Config(
        canvas_api_token=token,
        canvas_base_url=base_url,
        credentials_dir=credentials_dir,
    )
