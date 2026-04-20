#!/usr/bin/env python3
"""
T-Shirt Image Workflow
======================
Automates the full pipeline from raw garment photos to multi-pose
fashion renders using Higgsfield AI.

Workflow steps
--------------
1. Scan the input directory for design folders
2. For each design folder, locate the raw t-shirt image
3. Upload the raw image to Higgsfield
4. Apply the configured generation prompt
5. Generate the base model image wearing the t-shirt
6. Download the generated base image and re-upload to Higgsfield
7. Generate multiple pose variations from the base model image
8. Save everything into a dedicated output folder for that design

Credentials
-----------
Set HF_KEY in your .env file:
    HF_KEY=<api_key_id>:<api_secret>

Get your credentials from https://cloud.higgsfield.ai

Usage
-----
    python workflow.py                          # use default config.yaml
    python workflow.py --config my_config.yaml
    python workflow.py --input tshirts/ --output output/
    python workflow.py --design monarch         # single design
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from tqdm import tqdm

import higgsfield_client as hf
from hf_utils import download_image

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def apply_cli_overrides(cfg: dict, args: argparse.Namespace) -> dict:
    if args.input:
        cfg["input_dir"] = args.input
    if args.output:
        cfg["output_dir"] = args.output
    return cfg


# ---------------------------------------------------------------------------
# Step 1 — discover design folders
# ---------------------------------------------------------------------------

def discover_designs(input_dir: str, extensions: list[str]) -> list[dict]:
    root = Path(input_dir)
    if not root.exists():
        log.error("Input directory not found: %s", root)
        sys.exit(1)

    exts = {e.lower() for e in extensions}
    designs = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        images = [f for f in sorted(folder.iterdir()) if f.is_file() and f.suffix.lower() in exts]
        if not images:
            log.warning("Skipping '%s' — no image file found", folder.name)
            continue
        if len(images) > 1:
            log.warning("Multiple images in '%s'; using: %s", folder.name, images[0].name)
        designs.append({"name": folder.name, "raw_image": images[0]})

    log.info("Found %d design folder(s) in '%s'", len(designs), input_dir)
    return designs


# ---------------------------------------------------------------------------
# Per-design pipeline
# ---------------------------------------------------------------------------

def process_design(design: dict, cfg: dict) -> None:
    name = design["name"]
    raw_image: Path = design["raw_image"]
    output_dir = Path(cfg["output_dir"]) / name
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("━━━  %s  ━━━", name)

    # ── Step 3 — upload raw garment image ─────────────────────────────────
    log.info("[%s] Step 3 — Uploading raw t-shirt image…", name)
    garment_url = hf.upload_file(str(raw_image))
    log.info("[%s] Garment URL: %s", name, garment_url)

    # ── Step 4 & 5 — generate base model image ────────────────────────────
    log.info("[%s] Step 4/5 — Generating base model image (may take ~60s)…", name)

    base_model_cfg = cfg["base_model"]
    result = hf.subscribe(
        base_model_cfg["application"],
        arguments={
            **base_model_cfg.get("arguments", {}),
            "prompt": cfg["generation_prompt"],
            "image_url": garment_url,
        },
        on_queue_update=lambda s: log.info("[%s] Status: %s", name, type(s).__name__),
    )

    base_urls = _extract_urls(result)
    log.info("[%s] Base image(s) ready — %d result(s)", name, len(base_urls))

    # ── Step 6 — download base image and re-upload ────────────────────────
    base_uploaded_urls = []
    for idx, url in enumerate(base_urls):
        local_name = f"base_model_{idx + 1}{_ext(url)}"
        local_path = output_dir / local_name
        log.info("[%s] Step 6 — Downloading → %s", name, local_name)
        download_image(url, str(local_path))

        log.info("[%s] Re-uploading base image for pose generation…", name)
        reuploaded_url = hf.upload_file(str(local_path))
        base_uploaded_urls.append(reuploaded_url)
        log.info("[%s] Re-upload done: %s", name, reuploaded_url)

    # ── Step 7 & 8 — generate and save pose variations ────────────────────
    poses: list[str] = cfg.get("poses", [])
    if not poses:
        log.warning("[%s] No poses configured — skipping pose step", name)
        return

    pose_model_cfg = cfg["pose_model"]

    for base_idx, model_url in enumerate(base_uploaded_urls):
        log.info("[%s] Step 7 — Generating %d pose(s) from base image %d…", name, len(poses), base_idx + 1)

        for pose_idx, pose in enumerate(poses):
            log.info("[%s]   Pose %d/%d: %s", name, pose_idx + 1, len(poses), pose)
            pose_result = hf.subscribe(
                pose_model_cfg["application"],
                arguments={
                    **pose_model_cfg.get("arguments", {}),
                    "image_url": model_url,
                    "prompt": f"{cfg.get('pose_prompt', '')} {pose}".strip(),
                },
                on_queue_update=lambda s: log.info("[%s]   Status: %s", name, type(s).__name__),
            )

            pose_urls = _extract_urls(pose_result)
            for img_idx, url in enumerate(pose_urls):
                label = _safe_name(pose)
                filename = f"pose_{pose_idx + 1}_{label}{_ext(url)}"
                dest = output_dir / filename
                download_image(url, str(dest))
                log.info("[%s] Step 8 — Saved: %s", name, dest)

    log.info("[%s] Done. Output folder: %s", name, output_dir)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="T-shirt image workflow via Higgsfield AI")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--input", help="Override input_dir")
    parser.add_argument("--output", help="Override output_dir")
    parser.add_argument("--design", help="Process only this design folder name")
    args = parser.parse_args()

    if not os.getenv("HF_KEY"):
        log.error(
            "HF_KEY is not set.\n"
            "Add to your .env file:  HF_KEY=<api_key_id>:<api_secret>\n"
            "Get credentials from:   https://cloud.higgsfield.ai"
        )
        sys.exit(1)

    cfg = apply_cli_overrides(load_config(args.config), args)
    designs = discover_designs(cfg["input_dir"], cfg["image_extensions"])

    if not designs:
        log.error("No designs found in '%s'.", cfg["input_dir"])
        sys.exit(1)

    if args.design:
        designs = [d for d in designs if d["name"] == args.design]
        if not designs:
            log.error("Design '%s' not found.", args.design)
            sys.exit(1)

    log.info("Starting workflow for %d design(s)…", len(designs))

    for design in tqdm(designs, desc="Designs", unit="design"):
        try:
            process_design(design, cfg)
        except Exception as exc:
            log.error("Failed on '%s': %s", design["name"], exc, exc_info=True)
            log.info("Continuing with next design…")

    log.info("All done. Results in '%s/'", cfg["output_dir"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_urls(result: dict) -> list[str]:
    """Pull image URLs out of any Higgsfield response shape."""
    if isinstance(result, dict):
        for key in ("images", "output_urls", "outputs", "results"):
            val = result.get(key)
            if isinstance(val, list):
                # Each element may be a dict with a 'url' key or a plain string
                urls = []
                for item in val:
                    if isinstance(item, dict):
                        urls.append(item.get("url") or item.get("image_url") or "")
                    elif isinstance(item, str):
                        urls.append(item)
                return [u for u in urls if u]
        # Fallback: single image
        for key in ("image", "url", "image_url", "output"):
            if result.get(key):
                return [result[key]]
    return []


def _ext(url: str) -> str:
    suffix = Path(url.split("?")[0]).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def _safe_name(text: str) -> str:
    return text.lower().replace(" ", "_").replace(",", "").replace("/", "_")[:40]


if __name__ == "__main__":
    main()
