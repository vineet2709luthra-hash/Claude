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
5. Generate the base model image(s) wearing the t-shirt
6. Download the generated base image and re-upload to Higgsfield
7. Generate multiple pose variations from the base model image
8. Save everything into a dedicated output folder for that design

Usage
-----
    # Set your API key in the environment or .env file
    export HIGGSFIELD_API_KEY=your_key_here

    python workflow.py                        # use default config.yaml
    python workflow.py --config my_config.yaml
    python workflow.py --input tshirts/ --output output/
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from tqdm import tqdm

from higgsfield_client import HiggsfieldClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> dict:
    with open(config_path) as fh:
        return yaml.safe_load(fh)


def resolve_paths(cfg: dict, args: argparse.Namespace) -> dict:
    """CLI flags override config file values."""
    if args.input:
        cfg["input_dir"] = args.input
    if args.output:
        cfg["output_dir"] = args.output
    return cfg


# ---------------------------------------------------------------------------
# Step 1 — Discover design folders
# ---------------------------------------------------------------------------

def discover_designs(input_dir: str, image_extensions: list[str]) -> list[dict]:
    """
    Scan input_dir for sub-folders that contain at least one image file.
    Returns a list of dicts: {name, folder_path, raw_image_path}
    """
    root = Path(input_dir)
    if not root.exists():
        log.error("Input directory does not exist: %s", root)
        sys.exit(1)

    extensions = {ext.lower() for ext in image_extensions}
    designs = []

    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        images = [
            f for f in sorted(folder.iterdir())
            if f.is_file() and f.suffix.lower() in extensions
        ]
        if not images:
            log.warning("Skipping '%s' — no image found", folder.name)
            continue
        if len(images) > 1:
            log.warning(
                "Multiple images in '%s'; using first: %s",
                folder.name, images[0].name,
            )
        designs.append({
            "name": folder.name,
            "folder_path": folder,
            "raw_image_path": images[0],
        })

    log.info("Found %d design folder(s) in '%s'", len(designs), input_dir)
    return designs


# ---------------------------------------------------------------------------
# Per-design pipeline
# ---------------------------------------------------------------------------

def process_design(design: dict, cfg: dict, client: HiggsfieldClient) -> None:
    name = design["name"]
    raw_image = design["raw_image_path"]
    output_root = Path(cfg["output_dir"]) / name
    output_root.mkdir(parents=True, exist_ok=True)

    log.info("━━━ Processing design: %s ━━━", name)

    # ── Step 2 already done (raw_image_path resolved in discover_designs) ──

    # ── Step 3 — Upload raw t-shirt image ──────────────────────────────────
    log.info("[%s] Step 3 — Uploading raw image: %s", name, raw_image.name)
    garment_asset_id = client.upload_image(str(raw_image))
    log.info("[%s] Uploaded garment asset_id=%s", name, garment_asset_id)

    # ── Step 4 & 5 — Generate base model image ─────────────────────────────
    log.info("[%s] Step 4/5 — Generating base model image…", name)
    job_id = client.generate_model_with_tshirt(
        garment_asset_id=garment_asset_id,
        prompt=cfg["generation_prompt"],
        negative_prompt=cfg.get("generation_negative_prompt", ""),
        num_images=cfg.get("num_base_images", 1),
    )
    log.info("[%s] Generation job submitted: %s", name, job_id)
    base_urls = client.wait_for_job(
        job_id,
        poll_interval=cfg.get("poll_interval_seconds", 5),
        timeout=cfg.get("job_timeout_seconds", 300),
    )
    log.info("[%s] Base image(s) ready (%d result(s))", name, len(base_urls))

    # ── Step 6 — Download base image & re-upload ───────────────────────────
    base_images_uploaded = []
    for idx, url in enumerate(base_urls):
        local_name = f"base_model_{idx + 1}{_ext_from_url(url)}"
        local_path = output_root / local_name
        log.info("[%s] Step 6 — Downloading base image → %s", name, local_name)
        client.download_image(url, str(local_path))

        log.info("[%s] Re-uploading base image for pose generation…", name)
        model_asset_id = client.upload_image(str(local_path))
        base_images_uploaded.append(model_asset_id)
        log.info("[%s] Re-uploaded as asset_id=%s", name, model_asset_id)

    # ── Step 7 — Generate pose variations ─────────────────────────────────
    poses = cfg.get("poses", [])
    if not poses:
        log.warning("[%s] No poses configured — skipping pose generation", name)
        return

    for base_idx, model_asset_id in enumerate(base_images_uploaded):
        log.info(
            "[%s] Step 7 — Generating %d pose(s) from base image %d…",
            name, len(poses), base_idx + 1,
        )
        pose_job_id = client.generate_poses(
            model_asset_id=model_asset_id,
            poses=poses,
            prompt=cfg.get("pose_prompt", ""),
            negative_prompt=cfg.get("pose_negative_prompt", ""),
        )
        log.info("[%s] Pose job submitted: %s", name, pose_job_id)
        pose_urls = client.wait_for_job(
            pose_job_id,
            poll_interval=cfg.get("poll_interval_seconds", 5),
            timeout=cfg.get("job_timeout_seconds", 300),
        )

        # ── Step 8 — Save pose images into design folder ───────────────────
        log.info("[%s] Step 8 — Saving %d pose image(s)…", name, len(pose_urls))
        for pose_idx, url in enumerate(pose_urls):
            pose_label = _safe_filename(poses[pose_idx]) if pose_idx < len(poses) else f"pose_{pose_idx + 1}"
            file_name = f"pose_{pose_idx + 1}_{pose_label}{_ext_from_url(url)}"
            dest = output_root / file_name
            client.download_image(url, str(dest))
            log.info("[%s] Saved: %s", name, dest.relative_to(Path(cfg["output_dir"]).parent))

    log.info("[%s] Done — output folder: %s", name, output_root)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated t-shirt image workflow using Higgsfield AI"
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--input", help="Override input_dir from config")
    parser.add_argument("--output", help="Override output_dir from config")
    parser.add_argument(
        "--design",
        help="Process only this design folder name (skip others)",
    )
    args = parser.parse_args()

    cfg = resolve_paths(load_config(args.config), args)

    api_key = os.getenv("HIGGSFIELD_API_KEY")
    if not api_key:
        log.error(
            "HIGGSFIELD_API_KEY environment variable not set. "
            "Add it to your .env file or export it before running."
        )
        sys.exit(1)

    client = HiggsfieldClient(api_key=api_key)

    # Step 1 — discover designs
    designs = discover_designs(cfg["input_dir"], cfg["image_extensions"])
    if not designs:
        log.error("No designs found. Check your input directory.")
        sys.exit(1)

    # Optional filter: process only one design
    if args.design:
        designs = [d for d in designs if d["name"] == args.design]
        if not designs:
            log.error("Design '%s' not found.", args.design)
            sys.exit(1)

    log.info("Starting workflow for %d design(s)…", len(designs))

    # Step 2–8 — process each design folder in order
    for design in tqdm(designs, desc="Designs", unit="design"):
        try:
            process_design(design, cfg, client)
        except Exception as exc:
            log.error("Failed to process '%s': %s", design["name"], exc)
            log.info("Continuing with next design…")

    log.info("Workflow complete. Check the '%s' directory.", cfg["output_dir"])


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _ext_from_url(url: str) -> str:
    """Extract file extension from URL, defaulting to .jpg."""
    path = url.split("?")[0]
    ext = Path(path).suffix.lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def _safe_filename(text: str) -> str:
    """Convert a pose description into a safe filename fragment."""
    return (
        text.lower()
        .replace(" ", "_")
        .replace(",", "")
        .replace("/", "_")
        [:40]
    )


if __name__ == "__main__":
    main()
