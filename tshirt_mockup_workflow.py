#!/usr/bin/env python3
"""
T-Shirt E-Commerce Campaign Generator — HiggsField Nano Banana Pro 4K

Workflow:
  1. Give me ANY folder — I auto-detect every design and its front/back images
  2. I describe the model ONCE and reuse that description in every generation
  3. I upload the garment images to HiggsField CDN automatically
  4. I generate 8 e-commerce poses per design using Nano Banana Pro 4K
  5. I save everything to organized output folders ready for Myntra / Amazon

Handles ANY input structure — no renaming or reorganizing needed:
  ✓ Subfolders with named files   (design1/front.jpg, design1/back.jpg)
  ✓ Subfolders with unnamed files (design1/img001.jpg, design1/img002.jpg)
  ✓ Flat folder with all images   (red_tshirt_1.jpg, red_tshirt_2.jpg, ...)
  ✓ Mixed / deeply nested         (auto-crawled)
  ✓ Any image format              (.jpg, .jpeg, .png, .webp)

Usage:
  python tshirt_mockup_workflow.py \
      --api-key   YOUR_KEY \          # or set HIGGSFIELD_API_KEY env var
      --soul-id   YOUR_SOUL_ID \      # from higgsfield.ai/soul-intro
      --input     /path/to/tshirts \
      --output    /path/to/output     # optional
      --scan-only                     # preview detected designs without generating

Output structure:
  output/
    design1/
      design1_1_front_white.jpg       ← Amazon/Myntra main listing
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
import re
import sys
import time
import argparse
import requests
from pathlib import Path
from dataclasses import dataclass

# =============================================================================
# ✏️  MODEL DESCRIPTION — described ONCE, reused in every generation prompt
# =============================================================================

MODEL_DESCRIPTION = (
    "25-year-old Indian female model, athletic build, medium-warm brown skin tone, "
    "long straight black hair falling past shoulders, natural minimal makeup, "
    "sharp jawline, confident and relaxed posture"
)

# =============================================================================
# E-COMMERCE POSES — 8 per design, platform-tagged
# =============================================================================

ECOMMERCE_POSES = [
    {
        "name":     "1_front_white",
        "platform": "Amazon & Myntra — main listing",
        "side":     "front",
        "prompt": (
            "{model} wearing a t-shirt with {garment} design, "
            "standing straight facing camera, arms relaxed at sides, "
            "pure white seamless background, full body head to toe, "
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
            "three-quarter angle slight turn left, weight shifted on one leg, "
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
            "side profile view standing straight, "
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
            "dynamic confident walking pose mid-stride, slight smile, hair in motion, "
            "light grey seamless background, full body shot, "
            "fashion campaign lighting, high-energy editorial, ultra high quality 4K"
        ),
        "aspect_ratio": "3:4",
        "quality":      "4k",
    },
    {
        "name":     "6_lifestyle",
        "platform": "Myntra & Amazon — lifestyle",
        "side":     "front",
        "prompt": (
            "{model} wearing a t-shirt with {garment} design, "
            "casual relaxed pose leaning against minimalist white wall, slight smile, "
            "soft natural daylight from left, modern urban setting, "
            "fashion lifestyle photography, ultra high quality 4K"
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
            "chest and torso only in frame, exact design colors graphics and print sharp, "
            "pure white background, macro product detail photography, ultra high quality 4K"
        ),
        "aspect_ratio": "1:1",
        "quality":      "4k",
    },
    {
        "name":     "8_flat_lay",
        "platform": "Amazon & Myntra — flat lay",
        "side":     "front",
        "prompt": (
            "Overhead flat lay of a t-shirt with {garment} design on pure white surface, "
            "garment neatly spread showing exact design colors and print, no wrinkles, "
            "soft even studio lighting from above, professional product photography, "
            "ultra high quality 4K"
        ),
        "aspect_ratio": "1:1",
        "quality":      "4k",
    },
]

# =============================================================================
# API CONFIG
# =============================================================================

API_BASE         = "https://cloud.higgsfield.ai/api"
UPLOAD_ENDPOINT  = f"{API_BASE}/upload"
JOBS_ENDPOINT    = f"{API_BASE}/jobs/nano-banana-pro"
STATUS_ENDPOINT  = f"{API_BASE}/jobs"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
FRONT_KEYWORDS   = ["front", "f_", "_f.", "front_view", "_front", "-front"]
BACK_KEYWORDS    = ["back",  "b_", "_b.", "back_view",  "_back",  "-back"]

GENERATION_TIMEOUT = 600
POLL_INTERVAL      = 10

# =============================================================================
# DESIGN — holds one t-shirt design's front + back image paths
# =============================================================================

@dataclass
class Design:
    name:  str
    front: Path | None
    back:  Path | None

    def is_valid(self) -> bool:
        return self.front is not None or self.back is not None

    def summary(self) -> str:
        f = self.front.name if self.front else "MISSING"
        b = self.back.name  if self.back  else "MISSING"
        return f"front={f}  back={b}"

# =============================================================================
# SMART FOLDER SCANNER — handles ANY input structure
# =============================================================================

def _is_image(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS


def _keyword_side(path: Path) -> str | None:
    """Return 'front', 'back', or None based on filename keywords."""
    name = path.stem.lower()
    if any(kw in name for kw in ["front", "f_", "_f", "front_view"]):
        return "front"
    if any(kw in name for kw in ["back", "b_", "_b", "back_view"]):
        return "back"
    return None


def _common_prefix(name: str) -> str:
    """Strip trailing numbers/separators to get a design group key."""
    stem = re.sub(r'[\s_\-\.]*\d+$', '', name).strip('_- .') or name
    return stem.lower()


def _pair_images(images: list[Path]) -> tuple[Path | None, Path | None]:
    """
    Given a list of images for one design, return (front, back).
    Priority: keyword match → alphabetical order (first=front, second=back).
    """
    front = next((i for i in images if _keyword_side(i) == "front"), None)
    back  = next((i for i in images if _keyword_side(i) == "back"),  None)
    if not front or not back:
        ordered = sorted(images, key=lambda p: p.name)
        if not front and ordered:
            front = ordered[0]
        if not back and len(ordered) >= 2:
            back = ordered[1]
    return front, back


def scan_folder(root: Path) -> list[Design]:
    """
    Auto-detect all designs in ANY folder structure.

    Strategy:
      1. If root has subfolders containing images → each subfolder = one design
      2. If root is a flat folder with images → group by common filename prefix
         (e.g. red_tshirt_1.jpg + red_tshirt_2.jpg → design "red_tshirt")
      3. If no clear prefix grouping → pair images sequentially (1st+2nd, 3rd+4th …)
    """
    designs: list[Design] = []

    # --- Case 1: subfolders with images ---
    subfolders = [f for f in sorted(root.iterdir()) if f.is_dir()]
    sub_with_images = [d for d in subfolders if any(_is_image(f) for f in d.iterdir())]

    if sub_with_images:
        for folder in sub_with_images:
            images = [f for f in folder.iterdir() if _is_image(f)]
            front, back = _pair_images(images)
            designs.append(Design(name=folder.name, front=front, back=back))
        return designs

    # --- Case 2 / 3: flat folder ---
    all_images = sorted([f for f in root.iterdir() if _is_image(f)], key=lambda p: p.name)
    if not all_images:
        # Recurse one level deeper
        for sub in subfolders:
            designs.extend(scan_folder(sub))
        return designs

    # Group by common filename prefix
    groups: dict[str, list[Path]] = {}
    for img in all_images:
        prefix = _common_prefix(img.stem)
        groups.setdefault(prefix, []).append(img)

    # If every group has ≤ 2 images → good grouping, use it
    max_group_size = max(len(v) for v in groups.values())
    if max_group_size <= 2:
        for prefix, images in groups.items():
            front, back = _pair_images(images)
            name = prefix if prefix else f"design_{len(designs)+1:02d}"
            designs.append(Design(name=name, front=front, back=back))
    else:
        # Fallback: pair sequentially, name by index
        for i in range(0, len(all_images), 2):
            chunk = all_images[i:i+2]
            front, back = _pair_images(chunk)
            name = _common_prefix(chunk[0].stem) or f"design_{i//2+1:02d}"
            designs.append(Design(name=name, front=front, back=back))

    return designs


def print_scan_report(designs: list[Design], input_root: Path):
    """Print a clear report of what was detected before generating."""
    print(f"\n{'='*60}")
    print(f"  FOLDER SCAN REPORT")
    print(f"  Scanned: {input_root}")
    print(f"{'='*60}")
    if not designs:
        print("  No designs detected. Check that your folder contains images.")
        return
    print(f"  Found {len(designs)} design(s):\n")
    for i, d in enumerate(designs, 1):
        status = "OK" if d.front and d.back else ("FRONT ONLY" if d.front else "BACK ONLY")
        print(f"  [{i:02d}] {d.name:<30} [{status}]")
        print(f"        front : {d.front.name  if d.front else '— not found'}")
        print(f"        back  : {d.back.name   if d.back  else '— not found'}")
    print(f"\n  Will generate {len(designs) * len(ECOMMERCE_POSES)} images total "
          f"({len(ECOMMERCE_POSES)} poses × {len(designs)} designs)")
    print(f"{'='*60}\n")

# =============================================================================
# API HELPERS
# =============================================================================

def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def upload_image(api_key: str, image_path: Path) -> str:
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
    payload: dict = {
        "prompt":       prompt,
        "input_images": [garment_url],
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
                or (data.get("images")  or [None])[0]
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
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=16_384):
            fh.write(chunk)

# =============================================================================
# CORE: process one design
# =============================================================================

def process_design(api_key: str, soul_id: str | None,
                   design: Design, output_base: Path):
    out_dir = output_base / design.name
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Uploading garment for '{design.name}' …")
    front_url = upload_image(api_key, design.front) if design.front else None
    back_url  = upload_image(api_key, design.back)  if design.back  else None

    garment_label = design.name.replace("_", " ").replace("-", " ")
    total = len(ECOMMERCE_POSES)

    for i, pose in enumerate(ECOMMERCE_POSES, 1):
        save_path = out_dir / f"{design.name}_{pose['name']}.jpg"
        if save_path.exists():
            print(f"  [{i}/{total}] SKIP (exists): {save_path.name}")
            continue

        garment_url = back_url if pose["side"] == "back" else front_url
        if garment_url is None:
            print(f"  [{i}/{total}] SKIP (missing {'back' if pose['side']=='back' else 'front'}): {pose['name']}")
            continue

        prompt = pose["prompt"].format(model=MODEL_DESCRIPTION, garment=garment_label)

        print(f"\n  [{i}/{total}] {pose['name']}  ({pose['platform']})")
        print(f"        Submitting to Nano Banana Pro 4K …")
        job_id = submit_generation(api_key, prompt, garment_url, soul_id,
                                   pose["aspect_ratio"], pose["quality"])
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
        description="T-Shirt E-Commerce Campaign — HiggsField Nano Banana Pro 4K"
    )
    parser.add_argument("--api-key",   default=os.environ.get("HIGGSFIELD_API_KEY"),
                        help="HiggsField API key (or set HIGGSFIELD_API_KEY env var)")
    parser.add_argument("--soul-id",   default=None,
                        help="Soul ID for consistent model (higgsfield.ai/soul-intro)")
    parser.add_argument("--input",     required=True, help="Your t-shirt images folder")
    parser.add_argument("--output",    default=None,  help="Output folder (default: <input>_campaign)")
    parser.add_argument("--scan-only", action="store_true",
                        help="Preview detected designs without generating anything")
    args = parser.parse_args()

    input_root  = Path(args.input).expanduser().resolve()
    output_root = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_root.parent / f"{input_root.name}_campaign"
    )

    if not input_root.exists():
        sys.exit(f"ERROR: Folder not found: {input_root}")

    # Step 1: Scan and report
    print(f"\nScanning folder: {input_root}")
    designs = scan_folder(input_root)
    print_scan_report(designs, input_root)

    if args.scan_only:
        print("  --scan-only mode: no images generated.")
        return

    if not designs:
        sys.exit("No designs found. Nothing to generate.")

    if not args.api_key:
        sys.exit("ERROR: provide --api-key or set HIGGSFIELD_API_KEY env var")

    output_root.mkdir(parents=True, exist_ok=True)

    print(f"  Output  : {output_root}")
    print(f"  Soul ID : {args.soul_id or '(none)'}")
    print(f"  Model   : {MODEL_DESCRIPTION[:60]}…\n")

    for idx, design in enumerate(designs, 1):
        if not design.is_valid():
            print(f"[{idx}/{len(designs)}] SKIP {design.name} — no images found")
            continue
        print(f"\n{'='*60}")
        print(f"  Design [{idx}/{len(designs)}]: {design.name}")
        print(f"  {design.summary()}")
        print(f"{'='*60}")
        try:
            process_design(args.api_key, args.soul_id, design, output_root)
        except Exception as exc:
            print(f"  [ERROR] {exc}")

    print(f"\n{'='*60}")
    print(f"  Campaign complete! Saved to: {output_root}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
