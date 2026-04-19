#!/usr/bin/env python3
"""
T-Shirt E-Commerce Campaign Generator — HiggsField Nano Banana Pro 4K

Workflow:
  1. Describe your model ONCE at the top (MODEL_DESCRIPTION)
  2. Script scans input folder for design subfolders (front + back images each)
  3. Uploads garment images to HiggsField CDN
  4. Generates 8 e-commerce poses per design using Nano Banana Pro 4K
     — same model description + garment reference fed into every generation
  5. Saves to organized output folders ready for Myntra / Amazon upload

Usage:
  python tshirt_mockup_workflow.py \
      --api-key  YOUR_KEY \           # or set HIGGSFIELD_API_KEY env var
      --soul-id  YOUR_SOUL_ID \       # from higgsfield.ai/soul-intro (20+ photos)
      --input    /path/to/tshirts \
      --output   /path/to/output      # optional

Output structure:
  output/
    design1/
      design1_1_front_white.jpg          ← Amazon/Myntra main image
      design1_2_back_white.jpg
      design1_3_front_angle.jpg
      design1_4_side_profile.jpg
      design1_5_action_pose.jpg
      design1_6_lifestyle.jpg
      design1_7_detail_closeup.jpg
      design1_8_flat_lay.jpg
    design2/
      ...
"""

import os
import sys
import time
import argparse
import requests
from pathlib import Path

# =============================================================================
# ✏️  CONFIGURE YOUR MODEL HERE — described ONCE, reused in every generation
# =============================================================================

MODEL_DESCRIPTION = (
    "25-year-old Indian female model, athletic build, medium-warm brown skin tone, "
    "long straight black hair falling past shoulders, natural minimal makeup, "
    "sharp jawline, confident and relaxed posture"
)

# =============================================================================
# E-COMMERCE POSE DEFINITIONS
# Each pose gets its own subfolder-friendly name and platform tag.
# {model} and {garment} are filled in at runtime.
# =============================================================================

ECOMMERCE_POSES = [
    {
        "name":     "1_front_white",
        "platform": "Amazon & Myntra — main listing image",
        "side":     "front",
        "prompt": (
            "{model} wearing a t-shirt with {garment} design, "
            "standing straight facing camera, arms relaxed at sides, "
            "pure white seamless background, full body visible from head to toe, "
            "sharp studio lighting, e-commerce product photography, ultra high quality"
        ),
        "aspect_ratio": "3:4",
        "quality":      "4k",
    },
    {
        "name":     "2_back_white",
        "platform": "Amazon & Myntra — back view",
        "side":     "back",
        "prompt": (
            "{model} wearing a t-shirt with {garment} design, "
            "standing straight with back to camera, arms relaxed at sides, "
            "pure white seamless background, full body shot, "
            "sharp studio lighting, e-commerce product photography, ultra high quality"
        ),
        "aspect_ratio": "3:4",
        "quality":      "4k",
    },
    {
        "name":     "3_front_angle",
        "platform": "Amazon & Myntra — alternate view",
        "side":     "front",
        "prompt": (
            "{model} wearing a t-shirt with {garment} design, "
            "three-quarter angle, slight turn to left, weight on one leg, "
            "pure white seamless background, full body visible, "
            "soft studio lighting, fashion editorial, ultra high quality 4K"
        ),
        "aspect_ratio": "3:4",
        "quality":      "4k",
    },
    {
        "name":     "4_side_profile",
        "platform": "Amazon & Myntra — side view",
        "side":     "front",
        "prompt": (
            "{model} wearing a t-shirt with {garment} design, "
            "side profile view, standing straight, "
            "pure white seamless background, full body visible, "
            "studio lighting, clean product shot, ultra high quality 4K"
        ),
        "aspect_ratio": "3:4",
        "quality":      "4k",
    },
    {
        "name":     "5_action_pose",
        "platform": "Myntra — lifestyle banner",
        "side":     "front",
        "prompt": (
            "{model} wearing a t-shirt with {garment} design, "
            "dynamic walking pose, mid-stride, slight smile, hair in natural motion, "
            "light grey seamless background, full body shot, "
            "fashion campaign lighting, high-energy editorial look, ultra high quality 4K"
        ),
        "aspect_ratio": "3:4",
        "quality":      "4k",
    },
    {
        "name":     "6_lifestyle",
        "platform": "Myntra & Amazon — lifestyle image",
        "side":     "front",
        "prompt": (
            "{model} wearing a t-shirt with {garment} design, "
            "casual relaxed pose leaning against a minimalist white wall, "
            "soft natural daylight from the left, slight smile, "
            "modern urban background, fashion lifestyle photography, ultra high quality 4K"
        ),
        "aspect_ratio": "3:4",
        "quality":      "4k",
    },
    {
        "name":     "7_detail_closeup",
        "platform": "Amazon & Myntra — design detail",
        "side":     "front",
        "prompt": (
            "Close-up cropped shot of {model} wearing a t-shirt with {garment} design, "
            "chest and torso only, design clearly visible and sharp, "
            "showing exact colors, graphics, and print of the garment, "
            "pure white background, macro product detail photography, ultra high quality 4K"
        ),
        "aspect_ratio": "1:1",
        "quality":      "4k",
    },
    {
        "name":     "8_flat_lay",
        "platform": "Amazon & Myntra — product flat lay",
        "side":     "front",
        "prompt": (
            "Overhead flat lay photography of a t-shirt with {garment} design "
            "laid flat on pure white surface, "
            "garment neatly spread showing exact design, colors, and print, "
            "no wrinkles, soft even studio lighting from above, "
            "professional product photography, ultra high quality 4K"
        ),
        "aspect_ratio": "1:1",
        "quality":      "4k",
    },
]

# =============================================================================
# API CONFIG
# =============================================================================

API_BASE          = "https://cloud.higgsfield.ai/api"
UPLOAD_ENDPOINT   = f"{API_BASE}/upload"
JOBS_ENDPOINT     = f"{API_BASE}/jobs/nano-banana-pro"
STATUS_ENDPOINT   = f"{API_BASE}/jobs"

IMAGE_EXTENSIONS  = {".jpg", ".jpeg", ".png", ".webp"}
FRONT_KEYWORDS    = ["front", "f_", "_f.", "front_view"]
BACK_KEYWORDS     = ["back",  "b_", "_b.", "back_view"]

GENERATION_TIMEOUT = 600
POLL_INTERVAL      = 10

# =============================================================================
# API HELPERS
# =============================================================================

def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def upload_image(api_key: str, image_path: Path) -> str:
    """Upload a local file → return hosted CDN URL."""
    ext  = image_path.suffix.lower().lstrip(".")
    mime = "image/png" if ext == "png" else "image/jpeg"
    size_kb = image_path.stat().st_size // 1024

    print(f"        Uploading {image_path.name} ({size_kb} KB) …")
    with open(image_path, "rb") as fh:
        resp = requests.post(
            UPLOAD_ENDPOINT,
            headers=_headers(api_key),
            files={"file": (image_path.name, fh, mime)},
            timeout=120,
        )
    if not resp.ok:
        raise RuntimeError(f"Upload failed [{resp.status_code}]: {resp.text}")

    data = resp.json()
    url  = data.get("url") or data.get("image_url") or data.get("data", {}).get("url")
    if not url:
        raise ValueError(f"Unexpected upload response: {data}")
    print(f"        CDN URL: {url}")
    return url


def submit_generation(api_key: str, prompt: str, garment_url: str,
                      soul_id: str | None, aspect_ratio: str, quality: str) -> str:
    """Submit a Nano Banana Pro generation job → return job ID."""
    payload: dict = {
        "prompt":       prompt,
        "input_images": [garment_url],   # garment used as visual reference
        "aspect_ratio": aspect_ratio,
        "quality":      quality,
    }
    if soul_id:
        payload["custom_reference_id"]       = soul_id
        payload["custom_reference_strength"] = 1.0

    resp = requests.post(
        JOBS_ENDPOINT,
        headers={**_headers(api_key), "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"Generation failed [{resp.status_code}]: {resp.text}")

    data   = resp.json()
    job_id = (
        data.get("job_id") or data.get("id")
        or data.get("generation_id")
        or data.get("data", {}).get("job_id")
    )
    if not job_id:
        raise ValueError(f"No job ID in response: {data}")
    return job_id


def poll_job(api_key: str, job_id: str) -> str:
    """Poll until job completes → return output image URL."""
    deadline = time.time() + GENERATION_TIMEOUT
    while time.time() < deadline:
        resp = requests.get(
            f"{STATUS_ENDPOINT}/{job_id}",
            headers=_headers(api_key),
            timeout=30,
        )
        resp.raise_for_status()
        data   = resp.json()
        status = data.get("status", "").lower()

        if status in ("completed", "succeeded", "done", "finished"):
            url = (
                data.get("output_url") or data.get("image_url")
                or data.get("url")
                or (data.get("outputs") or [None])[0]
                or (data.get("images") or [None])[0]
            )
            if not url:
                raise ValueError(f"No output URL in response: {data}")
            return url

        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"Job {job_id} failed: {data.get('error', status)}")

        print(f"        [{status}] waiting {POLL_INTERVAL}s …")
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Job {job_id} timed out after {GENERATION_TIMEOUT}s")


def download_image(url: str, save_path: Path):
    """Download generated image to disk."""
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=16_384):
            fh.write(chunk)

# =============================================================================
# FOLDER HELPERS
# =============================================================================

def find_side(folder: Path, keywords: list[str]) -> Path | None:
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
            if any(kw in f.name.lower() for kw in keywords):
                return f
    return None


def collect_images(folder: Path) -> tuple[Path | None, Path | None]:
    front = find_side(folder, FRONT_KEYWORDS)
    back  = find_side(folder, BACK_KEYWORDS)
    if not front or not back:
        all_imgs = sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not front and len(all_imgs) >= 1:
            front = all_imgs[0]
        if not back  and len(all_imgs) >= 2:
            back  = all_imgs[1]
    return front, back

# =============================================================================
# CORE: process one design
# =============================================================================

def process_design(api_key: str, soul_id: str | None,
                   design_folder: Path, output_base: Path):
    name    = design_folder.name
    out_dir = output_base / name
    out_dir.mkdir(parents=True, exist_ok=True)

    front_img, back_img = collect_images(design_folder)
    if not front_img and not back_img:
        print(f"  [SKIP] No images found in {design_folder}")
        return

    # Upload garment images once — reuse CDN URLs for all poses
    print(f"\n  Uploading garment images for '{name}' …")
    front_url = upload_image(api_key, front_img) if front_img else None
    back_url  = upload_image(api_key, back_img)  if back_img  else None

    garment_label = f"{name} t-shirt"

    total = len(ECOMMERCE_POSES)
    for i, pose in enumerate(ECOMMERCE_POSES, 1):
        save_path = out_dir / f"{name}_{pose['name']}.jpg"
        if save_path.exists():
            print(f"  [{i}/{total}] SKIP (exists): {save_path.name}")
            continue

        # Use front garment URL for front-facing poses, back URL for back poses
        garment_url = back_url if pose["side"] == "back" else front_url
        if garment_url is None:
            print(f"  [{i}/{total}] SKIP (no {'back' if pose['side'] == 'back' else 'front'} image): {pose['name']}")
            continue

        # Build final prompt: model description + garment reference + pose
        prompt = pose["prompt"].format(
            model   = MODEL_DESCRIPTION,
            garment = garment_label,
        )

        print(f"\n  [{i}/{total}] {pose['name']}  ({pose['platform']})")
        print(f"        Submitting to Nano Banana Pro 4K …")

        job_id = submit_generation(
            api_key, prompt, garment_url, soul_id,
            pose["aspect_ratio"], pose["quality"],
        )
        print(f"        Job ID: {job_id}")

        output_url = poll_job(api_key, job_id)

        print(f"        Downloading …")
        download_image(output_url, save_path)
        print(f"        Saved → {save_path}")

# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate t-shirt e-commerce campaign images via HiggsField Nano Banana Pro 4K"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("HIGGSFIELD_API_KEY"),
        help="HiggsField API key (or set HIGGSFIELD_API_KEY env var)",
    )
    parser.add_argument(
        "--soul-id",
        default=None,
        help="HiggsField Soul ID for consistent model across all images "
             "(create at higgsfield.ai/soul-intro with 20+ model photos)",
    )
    parser.add_argument("--input",  required=True, help="Folder containing design subfolders")
    parser.add_argument("--output", default=None,  help="Output folder (default: <input>_campaign)")
    args = parser.parse_args()

    if not args.api_key:
        sys.exit("ERROR: provide --api-key or set HIGGSFIELD_API_KEY environment variable")

    input_root  = Path(args.input).expanduser().resolve()
    output_root = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_root.parent / f"{input_root.name}_campaign"
    )

    if not input_root.exists():
        sys.exit(f"ERROR: Input folder not found: {input_root}")

    output_root.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  T-Shirt E-Commerce Campaign Generator")
    print("  Model: HiggsField Nano Banana Pro 4K")
    print("=" * 60)
    print(f"  Input      : {input_root}")
    print(f"  Output     : {output_root}")
    print(f"  Soul ID    : {args.soul_id or '(none)'}")
    print(f"  Poses/design: {len(ECOMMERCE_POSES)}")
    print(f"  Platforms  : Amazon + Myntra")
    print("=" * 60)
    print(f"\n  Model description:\n  {MODEL_DESCRIPTION}\n")

    design_folders = sorted(f for f in input_root.iterdir() if f.is_dir())

    if not design_folders:
        print(f"No subfolders found — treating {input_root.name} as a single design.")
        process_design(args.api_key, args.soul_id, input_root, output_root)
    else:
        print(f"Found {len(design_folders)} design(s). Generating {len(ECOMMERCE_POSES)} poses each.\n")
        for idx, folder in enumerate(design_folders, 1):
            print(f"\n{'='*60}")
            print(f"  Design [{idx}/{len(design_folders)}]: {folder.name}")
            print(f"{'='*60}")
            try:
                process_design(args.api_key, args.soul_id, folder, output_root)
            except Exception as exc:
                print(f"  [ERROR] {exc}")

    print(f"\n{'='*60}")
    print(f"  Campaign complete! Images saved to:")
    print(f"  {output_root}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
