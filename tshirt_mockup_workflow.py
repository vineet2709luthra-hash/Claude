#!/usr/bin/env python3
"""
T-Shirt Mockup Generator using HiggsField API

Workflow:
  1. Scans input folder for subfolders (each = one design, with front + back images)
  2. Uploads raw t-shirt images to HiggsField
  3. Generates professional mockups — same model in every image via Soul ID
  4. Saves results to organized output folders (one per design)

Usage:
  python tshirt_mockup_workflow.py \
      --api-key  YOUR_KEY \        # or set env var HIGGSFIELD_API_KEY
      --soul-id  YOUR_SOUL_ID \    # for consistent model across all images
      --input    /path/to/tshirts \
      --output   /path/to/output   # optional

How to get a Soul ID:
  1. Go to https://higgsfield.ai/soul-intro
  2. Upload 20+ photos of the model you want to use
  3. Wait ~3 min for training, copy the Soul ID UUID shown
  4. Pass it via --soul-id

Folder structure expected:
  tshirts/
    design1/
      front.jpg
      back.jpg
    design2/
      front.png
      back.png
"""

import os
import sys
import time
import argparse
import requests
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE          = "https://cloud.higgsfield.ai/api"
UPLOAD_ENDPOINT   = f"{API_BASE}/upload"
GENERATE_ENDPOINT = f"{API_BASE}/v1/generations"
STATUS_ENDPOINT   = f"{API_BASE}/v1/generations"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

FRONT_KEYWORDS = ["front", "f_", "_f.", "front_view"]
BACK_KEYWORDS  = ["back",  "b_", "_b.", "back_view"]

GENERATION_TIMEOUT = 600  # seconds to wait per image
POLL_INTERVAL      = 8    # seconds between status checks

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

FRONT_PROMPT = (
    "Professional fashion editorial photo, t-shirt front view clearly visible, "
    "model standing confidently in a modern studio, soft diffused lighting, "
    "pure white background, ultra sharp details, high-end apparel campaign"
)

BACK_PROMPT = (
    "Professional fashion editorial photo, t-shirt back view clearly visible, "
    "model standing confidently in a modern studio, soft diffused lighting, "
    "pure white background, ultra sharp details, high-end apparel campaign"
)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _auth_headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def upload_image(api_key: str, image_path: Path) -> str:
    """
    Upload a local image file to HiggsField and return its hosted CDN URL.
    The script opens the file, POSTs it as multipart form-data, and
    extracts the URL from the JSON response.
    """
    ext  = image_path.suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"

    print(f"      Opening {image_path.name} ({image_path.stat().st_size // 1024} KB) …")
    with open(image_path, "rb") as fh:
        resp = requests.post(
            UPLOAD_ENDPOINT,
            headers=_auth_headers(api_key),
            files={"file": (image_path.name, fh, mime)},
            timeout=120,
        )

    if not resp.ok:
        raise RuntimeError(f"Upload failed [{resp.status_code}]: {resp.text}")

    data = resp.json()
    url  = data.get("url") or data.get("image_url") or data.get("data", {}).get("url")
    if not url:
        raise ValueError(f"No URL in upload response: {data}")

    print(f"      Uploaded → {url}")
    return url


def start_generation(api_key: str, image_url: str, prompt: str,
                     soul_id: str | None) -> str:
    """
    Submit a generation job.
    - image_url          : CDN URL of the uploaded raw t-shirt image
    - soul_id            : HiggsField Soul ID — locks the same model in every image
    - custom_reference_strength: 1.0 = maximum model consistency
    - strength           : how much to restyle vs. preserve the source (0.55 = balanced)
    """
    payload: dict = {
        "model":        "higgsfield-soul-image-to-image",
        "image_url":    image_url,
        "prompt":       prompt,
        "strength":     0.55,
        "aspect_ratio": "1:1",
        "quality":      "high",
    }

    if soul_id:
        payload["custom_reference_id"]       = soul_id
        payload["custom_reference_strength"] = 1.0   # max consistency

    resp = requests.post(
        GENERATE_ENDPOINT,
        headers={**_auth_headers(api_key), "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )

    if not resp.ok:
        raise RuntimeError(f"Generation request failed [{resp.status_code}]: {resp.text}")

    data   = resp.json()
    gen_id = (
        data.get("generation_id")
        or data.get("id")
        or data.get("data", {}).get("generation_id")
    )
    if not gen_id:
        raise ValueError(f"No generation ID in response: {data}")
    return gen_id


def poll_generation(api_key: str, gen_id: str) -> str:
    """Poll until generation completes and return the output image URL."""
    deadline = time.time() + GENERATION_TIMEOUT
    while time.time() < deadline:
        resp = requests.get(
            f"{STATUS_ENDPOINT}/{gen_id}",
            headers=_auth_headers(api_key),
            timeout=30,
        )
        resp.raise_for_status()
        data   = resp.json()
        status = data.get("status", "").lower()

        if status in ("completed", "succeeded", "done"):
            out_url = (
                data.get("output_url")
                or data.get("image_url")
                or (data.get("outputs") or [None])[0]
            )
            if not out_url:
                raise ValueError(f"No output URL in completed response: {data}")
            return out_url

        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"Generation {gen_id} failed: {data.get('error', status)}")

        print(f"      status={status} — waiting {POLL_INTERVAL}s …")
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Generation {gen_id} timed out after {GENERATION_TIMEOUT}s")


def download_image(url: str, save_path: Path):
    """Stream-download a generated image to a local file."""
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=16_384):
            fh.write(chunk)

# ---------------------------------------------------------------------------
# Folder helpers
# ---------------------------------------------------------------------------

def find_side_image(folder: Path, keywords: list[str]) -> Path | None:
    """Return first image whose filename contains any of the given keywords."""
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
            if any(kw in f.name.lower() for kw in keywords):
                return f
    return None


def collect_images(folder: Path) -> tuple[Path | None, Path | None]:
    """Return (front_image, back_image) from a design folder."""
    front = find_side_image(folder, FRONT_KEYWORDS)
    back  = find_side_image(folder, BACK_KEYWORDS)

    if not front or not back:
        all_imgs = sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not front and len(all_imgs) >= 1:
            front = all_imgs[0]
        if not back and len(all_imgs) >= 2:
            back = all_imgs[1]

    return front, back

# ---------------------------------------------------------------------------
# Core processor
# ---------------------------------------------------------------------------

def process_design(api_key: str, soul_id: str | None,
                   design_folder: Path, output_base: Path):
    """Process one design: upload → generate (with Soul) → save."""
    name    = design_folder.name
    out_dir = output_base / name
    out_dir.mkdir(parents=True, exist_ok=True)

    front_img, back_img = collect_images(design_folder)

    if not front_img and not back_img:
        print(f"  [SKIP] No images found in {design_folder}")
        return

    for img, label, prompt in [
        (front_img, "front", FRONT_PROMPT),
        (back_img,  "back",  BACK_PROMPT),
    ]:
        if img is None:
            print(f"  [SKIP] No {label} image found for {name}")
            continue

        save_path = out_dir / f"{name}_{label}_mockup{img.suffix.lower()}"
        if save_path.exists():
            print(f"  [SKIP] Already generated: {save_path.name}")
            continue

        print(f"\n  [{label.upper()}] {img.name}")
        print(f"  [{label.upper()}] Step 1 — Uploading to HiggsField …")
        hosted_url = upload_image(api_key, img)

        print(f"  [{label.upper()}] Step 2 — Starting AI generation …")
        if soul_id:
            print(f"  [{label.upper()}]          Soul ID: {soul_id} (model consistency ON)")
        gen_id = start_generation(api_key, hosted_url, prompt, soul_id)
        print(f"  [{label.upper()}]          Job ID: {gen_id}")

        print(f"  [{label.upper()}] Step 3 — Waiting for result …")
        output_url = poll_generation(api_key, gen_id)

        print(f"  [{label.upper()}] Step 4 — Downloading mockup …")
        download_image(output_url, save_path)
        print(f"  [{label.upper()}] Saved → {save_path}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate t-shirt mockups via HiggsField AI with consistent model"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("HIGGSFIELD_API_KEY"),
        help="HiggsField API key (or set HIGGSFIELD_API_KEY env var)",
    )
    parser.add_argument(
        "--soul-id",
        default=None,
        help="HiggsField Soul ID — ensures the same model appears in every image. "
             "Create one at https://higgsfield.ai/soul-intro",
    )
    parser.add_argument("--input",  required=True, help="Folder containing design subfolders")
    parser.add_argument("--output", default=None,  help="Output folder (default: <input>_mockups)")
    args = parser.parse_args()

    if not args.api_key:
        sys.exit("ERROR: provide --api-key or set HIGGSFIELD_API_KEY environment variable")

    input_root  = Path(args.input).expanduser().resolve()
    output_root = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_root.parent / f"{input_root.name}_mockups"
    )

    if not input_root.exists():
        sys.exit(f"ERROR: Input folder not found: {input_root}")

    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Input   : {input_root}")
    print(f"Output  : {output_root}")
    print(f"Soul ID : {args.soul_id or '(none — model will vary per image)'}")
    print()

    design_folders = sorted(f for f in input_root.iterdir() if f.is_dir())

    if not design_folders:
        print(f"No subfolders found — treating {input_root.name} as a single design.")
        process_design(args.api_key, args.soul_id, input_root, output_root)
    else:
        print(f"Found {len(design_folders)} design folder(s).\n")
        for i, folder in enumerate(design_folders, 1):
            print(f"[{i}/{len(design_folders)}] {folder.name}")
            try:
                process_design(args.api_key, args.soul_id, folder, output_root)
            except Exception as exc:
                print(f"  [ERROR] {exc}")

    print(f"\nAll done! Mockups saved to: {output_root}")


if __name__ == "__main__":
    main()
