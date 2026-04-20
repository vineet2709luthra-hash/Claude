#!/usr/bin/env python3
"""
Higgsfield AI Agent
Automates the full Higgsfield workflow: authenticate → generate → poll → download

Steps captured from the platform:
  1. Authenticate with Bearer token
  2. Submit generation (text-to-image or image-to-video)
  3. Poll status until complete
  4. Download / save result
  5. (Optional) Cancel a pending job
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")

API_KEY  = os.getenv("HIGGSFIELD_API_KEY")
BASE_URL = "https://cloud.higgsfield.ai"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

POLL_INTERVAL = 5   # seconds between status checks
MAX_WAIT      = 600 # seconds before giving up


# ── Step 1 – Authenticate ─────────────────────────────────────────────────────

def authenticate():
    """Verify the API key is present and the service is reachable."""
    if not API_KEY:
        raise ValueError("HIGGSFIELD_API_KEY not set in .env")
    print(f"[1] Authenticated — key ends with ...{API_KEY[-6:]}")


# ── Step 2 – Submit generation ────────────────────────────────────────────────

def text_to_image(prompt: str, resolution: str = "1K", aspect_ratio: str = "16:9") -> str:
    """Submit a text-to-image request. Returns the job ID."""
    payload = {
        "task": "text-to-image",
        "model": "flux",
        "prompt": prompt,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
    }
    print(f"[2] Submitting text-to-image — prompt: {prompt!r}")
    resp = requests.post(f"{BASE_URL}/v1/generations", headers=HEADERS, json=payload)
    resp.raise_for_status()
    job_id = resp.json().get("id") or resp.json().get("generation_id")
    print(f"    Job ID: {job_id}")
    return job_id


def image_to_video(image_url: str, duration: int = 5, fps: int = 24,
                   motion_intensity: str = "medium") -> str:
    """Submit an image-to-video request. Returns the job ID."""
    payload = {
        "task": "image-to-video",
        "model": "default-video-model",
        "input_image": image_url,
        "duration": duration,
        "fps": fps,
        "motion_intensity": motion_intensity,
    }
    print(f"[2] Submitting image-to-video — source: {image_url}")
    resp = requests.post(f"{BASE_URL}/v1/generations", headers=HEADERS, json=payload)
    resp.raise_for_status()
    job_id = resp.json().get("id") or resp.json().get("generation_id")
    print(f"    Job ID: {job_id}")
    return job_id


# ── Step 3 – Poll status ──────────────────────────────────────────────────────

def poll_status(job_id: str) -> dict:
    """Poll until the job is done. Returns the completed response dict."""
    print(f"[3] Polling job {job_id} ...")
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        resp = requests.get(f"{BASE_URL}/v1/generations/{job_id}", headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "Unknown")
        print(f"    Status: {status}")

        if status == "Completed":
            print("    Done!")
            return data
        if status in ("Failed", "NSFW", "Cancelled"):
            raise RuntimeError(f"Job ended with status: {status}")

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Job {job_id} did not complete within {MAX_WAIT}s")


# ── Step 4 – Download result ──────────────────────────────────────────────────

def download_result(result: dict, output_dir: str = "outputs") -> Path:
    """Download the generated file and save it locally."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    url = result.get("output_url") or result.get("url")
    if not url:
        raise ValueError(f"No output URL in result: {result}")

    ext  = url.split("?")[0].split(".")[-1] or "bin"
    name = f"{result.get('id', 'output')}.{ext}"
    dest = output_path / name

    print(f"[4] Downloading result → {dest}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print(f"    Saved to {dest} ({dest.stat().st_size // 1024} KB)")
    return dest


# ── Step 5 – Cancel (optional) ────────────────────────────────────────────────

def cancel_job(job_id: str):
    """Cancel a queued or in-progress job."""
    resp = requests.delete(f"{BASE_URL}/v1/generations/{job_id}", headers=HEADERS)
    resp.raise_for_status()
    print(f"[5] Cancelled job {job_id}")


# ── Agent orchestrator ────────────────────────────────────────────────────────

class HiggsFieldAgent:
    """
    High-level agent that runs the full Higgsfield workflow.

    Usage:
        agent = HiggsFieldAgent()

        # Text → image
        path = agent.generate_image("A cinematic sunset over a futuristic city")

        # Image → video
        path = agent.generate_video(str(path))

        # Full pipeline: text → image → video
        video = agent.full_pipeline("A robot walking through a neon jungle")
    """

    def __init__(self):
        authenticate()

    def generate_image(self, prompt: str, **kwargs) -> Path:
        job_id = text_to_image(prompt, **kwargs)
        result = poll_status(job_id)
        return download_result(result)

    def generate_video(self, image_url: str, **kwargs) -> Path:
        job_id = image_to_video(image_url, **kwargs)
        result = poll_status(job_id)
        return download_result(result)

    def full_pipeline(self, prompt: str) -> Path:
        """Text → image → video in one call."""
        print("\n=== Higgsfield Full Pipeline ===")
        image_path = self.generate_image(prompt)
        video_path = self.generate_video(image_path.as_uri())
        print(f"\nFinal video: {video_path}")
        return video_path


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Higgsfield AI Agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_img = sub.add_parser("image", help="Generate image from text")
    p_img.add_argument("prompt")
    p_img.add_argument("--resolution", default="1K")
    p_img.add_argument("--aspect-ratio", default="16:9")

    p_vid = sub.add_parser("video", help="Generate video from image URL")
    p_vid.add_argument("image_url")
    p_vid.add_argument("--duration", type=int, default=5)
    p_vid.add_argument("--fps", type=int, default=24)
    p_vid.add_argument("--motion", default="medium", dest="motion_intensity")

    p_pipe = sub.add_parser("pipeline", help="Full text→image→video pipeline")
    p_pipe.add_argument("prompt")

    p_cancel = sub.add_parser("cancel", help="Cancel a job")
    p_cancel.add_argument("job_id")

    args = parser.parse_args()
    agent = HiggsFieldAgent()

    if args.cmd == "image":
        agent.generate_image(args.prompt, resolution=args.resolution,
                             aspect_ratio=args.aspect_ratio)
    elif args.cmd == "video":
        agent.generate_video(args.image_url, duration=args.duration,
                             fps=args.fps, motion_intensity=args.motion_intensity)
    elif args.cmd == "pipeline":
        agent.full_pipeline(args.prompt)
    elif args.cmd == "cancel":
        cancel_job(args.job_id)
