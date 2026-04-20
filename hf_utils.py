"""
Utility helpers that supplement the official higgsfield-client SDK.
Import the SDK directly as `import higgsfield_client as hf` in your scripts.
"""

import requests
from pathlib import Path


def download_image(url: str, dest_path: str) -> str:
    """Download a generated image URL to a local file. Returns dest_path."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            fh.write(chunk)
    return str(dest)
