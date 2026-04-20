"""
Higgsfield AI API client for t-shirt image generation workflow.
Handles asset upload, image generation, pose creation, and downloads.
"""

import time
import os
import requests
from pathlib import Path


class HiggsfieldClient:
    BASE_URL = "https://api.higgsfield.ai/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Asset management
    # ------------------------------------------------------------------

    def upload_image(self, image_path: str) -> str:
        """Upload a local image and return the asset_id."""
        path = Path(image_path)
        with open(path, "rb") as fh:
            resp = self.session.post(
                f"{self.BASE_URL}/assets/upload",
                files={"file": (path.name, fh, _mime_type(path))},
            )
        resp.raise_for_status()
        data = resp.json()
        return data["asset_id"]

    def get_asset_url(self, asset_id: str) -> str:
        """Return the public URL for a previously uploaded asset."""
        resp = self.session.get(f"{self.BASE_URL}/assets/{asset_id}")
        resp.raise_for_status()
        return resp.json()["url"]

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate_model_with_tshirt(
        self,
        garment_asset_id: str,
        prompt: str,
        negative_prompt: str = "",
        num_images: int = 1,
    ) -> str:
        """
        Submit a garment-on-model generation job.
        Returns job_id to poll with wait_for_job().
        """
        payload = {
            "garment_asset_id": garment_asset_id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_images": num_images,
            "mode": "garment_transfer",
        }
        resp = self.session.post(f"{self.BASE_URL}/generate", json=payload)
        resp.raise_for_status()
        return resp.json()["job_id"]

    def generate_poses(
        self,
        model_asset_id: str,
        poses: list[str],
        prompt: str = "",
        negative_prompt: str = "",
    ) -> str:
        """
        Submit a multi-pose generation job from an existing model image.
        poses: list of pose descriptors, e.g. ["front", "side", "back", "sitting"]
        Returns job_id.
        """
        payload = {
            "reference_asset_id": model_asset_id,
            "poses": poses,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "mode": "pose_variation",
        }
        resp = self.session.post(f"{self.BASE_URL}/generate", json=payload)
        resp.raise_for_status()
        return resp.json()["job_id"]

    # ------------------------------------------------------------------
    # Job polling
    # ------------------------------------------------------------------

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> list[str]:
        """
        Poll until job completes and return list of result image URLs.
        Raises TimeoutError if job doesn't finish within timeout seconds.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = self.session.get(f"{self.BASE_URL}/jobs/{job_id}")
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")

            if status == "completed":
                return data["output_urls"]
            if status == "failed":
                raise RuntimeError(
                    f"Job {job_id} failed: {data.get('error', 'unknown error')}"
                )
            time.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

    # ------------------------------------------------------------------
    # Download helper
    # ------------------------------------------------------------------

    def download_image(self, url: str, dest_path: str) -> str:
        """Download an image from url to dest_path. Returns dest_path."""
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        resp = self.session.get(url, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
        return str(dest)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _mime_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
