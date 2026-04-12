"""
models/dataset_setup.py
══════════════════════════════════════════════════════════════════
AgroSage — Dataset Setup & Merge Utility
══════════════════════════════════════════════════════════════════

This script helps you:
  1. Merge multiple datasets (PlantVillage + PlantDoc + others)
     into a unified class structure under dataset/raw/
  2. Show dataset statistics (class counts, imbalance report)
  3. Optionally cap over-represented classes for balance

USAGE
─────
  # Show stats on an existing dataset folder:
  python models/dataset_setup.py --stats dataset/raw

  # Merge two dataset sources into dataset/raw:
  python models/dataset_setup.py --merge \
      --sources /path/to/PlantVillage /path/to/PlantDoc \
      --output dataset/raw

  # Merge + cap each class at 2000 images:
  python models/dataset_setup.py --merge \
      --sources /path/to/PlantVillage /path/to/PlantDoc \
      --output dataset/raw --cap 2000

  # Show stats after merging:
  python models/dataset_setup.py --stats dataset/raw

──────────────────────────────────────────────────────────────
DATASET DOWNLOAD INSTRUCTIONS
──────────────────────────────────────────────────────────────

Option A — Kaggle CLI (fastest)
  pip install kaggle
  # Place kaggle.json in ~/.kaggle/ (from kaggle.com → Account → API)

  # PlantVillage (87k images, 38 classes — lab images):
  kaggle datasets download -d abdallahalidev/plantvillage-dataset
  unzip plantvillage-dataset.zip -d /tmp/plantvillage

  # PlantDoc (2.5k images, 27 classes — real-world field images):
  kaggle datasets download -d nirmalsankalana/plantdoc-dataset
  unzip plantdoc-dataset.zip -d /tmp/plantdoc

  # New Plant Diseases (87k, augmented PlantVillage variant):
  kaggle datasets download -d vipoooool/new-plant-diseases-dataset
  unzip new-plant-diseases-dataset.zip -d /tmp/newplant

  # Then merge:
  python models/dataset_setup.py --merge \
      --sources /tmp/plantvillage/PlantVillage \
                /tmp/plantdoc/train \
      --output dataset/raw

Option B — Manual download
  1. Visit https://www.kaggle.com/datasets/abdallahalidev/plantvillage-dataset
  2. Download ZIP and extract
  3. Put one folder per disease class under dataset/raw/
"""

import os
import shutil
import random
import argparse
from collections import Counter


SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


# ─────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────

def print_stats(data_dir: str) -> None:
    """Print class counts, imbalance ratio, and suggestions."""
    if not os.path.isdir(data_dir):
        print(f"❌  Directory not found: {data_dir}")
        return

    counts: dict[str, int] = {}
    for cls in sorted(os.listdir(data_dir)):
        cls_dir = os.path.join(data_dir, cls)
        if not os.path.isdir(cls_dir):
            continue
        n = sum(
            1 for f in os.listdir(cls_dir)
            if os.path.splitext(f)[1].lower() in SUPPORTED
        )
        if n > 0:
            counts[cls] = n

    if not counts:
        print("⚠️  No image classes found in", data_dir)
        return

    total = sum(counts.values())
    max_c = max(counts.values())
    min_c = min(counts.values())

    print("═" * 65)
    print(f"  Dataset statistics: {data_dir}")
    print("═" * 65)
    print(f"  Total classes : {len(counts)}")
    print(f"  Total images  : {total:,}")
    print(f"  Largest class : {max_c:,} images")
    print(f"  Smallest class: {min_c:,} images")
    print(f"  Imbalance ratio: {max_c / min_c:.1f}×")
    if max_c / min_c > 10:
        print("  ⚠️  High imbalance — consider --cap to balance classes")
    print()
    print(f"  {'Class':<55} {'Images':>7}")
    print("  " + "─" * 63)
    for cls, n in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "▓" * min(30, n // (max_c // 30 + 1))
        print(f"  {cls:<55} {n:>7,}  {bar}")
    print("═" * 65)
    print(f"\n  Ready to train? Run:")
    print(f"    python models/train_disease_v2.py --data {data_dir}")


# ─────────────────────────────────────────────────────────────
# Merge
# ─────────────────────────────────────────────────────────────

def _collect_images(src_dir: str) -> dict[str, list[str]]:
    """Walk src_dir and return {class_name: [image_paths]}."""
    result: dict[str, list[str]] = {}
    for cls in os.listdir(src_dir):
        cls_dir = os.path.join(src_dir, cls)
        if not os.path.isdir(cls_dir):
            continue
        imgs = [
            os.path.join(cls_dir, f)
            for f in os.listdir(cls_dir)
            if os.path.splitext(f)[1].lower() in SUPPORTED
        ]
        if imgs:
            result[cls] = imgs
    return result


def _normalise_class_name(name: str) -> str:
    """
    Normalise class names across datasets.
    PlantDoc uses spaces; PlantVillage uses underscores.
    We keep underscores for consistency.
    """
    return name.replace(" ", "_").strip()


def merge_datasets(
    sources: list[str],
    output_dir: str,
    cap: int | None = None,
    dry_run: bool = False,
) -> None:
    """
    Merge multiple dataset folders into output_dir.
    Images from all sources for the same (normalised) class are combined.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Collect everything
    merged: dict[str, list[str]] = {}
    for src in sources:
        if not os.path.isdir(src):
            print(f"⚠️  Source not found, skipping: {src}")
            continue
        print(f"  Scanning: {src}")
        for cls, imgs in _collect_images(src).items():
            norm = _normalise_class_name(cls)
            if norm not in merged:
                merged[norm] = []
            merged[norm].extend(imgs)

    if not merged:
        print("❌  No images found in any source directory.")
        return

    total_before = sum(len(v) for v in merged.values())
    print(f"\n  Classes: {len(merged)}  |  Images before cap: {total_before:,}")

    # Apply cap
    if cap:
        for cls in merged:
            if len(merged[cls]) > cap:
                merged[cls] = random.sample(merged[cls], cap)
        total_after = sum(len(v) for v in merged.values())
        print(f"  Images after cap ({cap}/class): {total_after:,}")

    if dry_run:
        print("\n  DRY RUN — no files copied.")
        for cls, imgs in sorted(merged.items()):
            print(f"  {cls:<55} {len(imgs):>6,}")
        return

    # Copy to output
    print(f"\n  Copying to: {output_dir}")
    for cls, imgs in sorted(merged.items()):
        cls_out = os.path.join(output_dir, cls)
        os.makedirs(cls_out, exist_ok=True)
        for i, src_path in enumerate(imgs):
            ext = os.path.splitext(src_path)[1].lower()
            dst = os.path.join(cls_out, f"{cls}_{i:06d}{ext}")
            if not os.path.exists(dst):   # avoid re-copying
                shutil.copy2(src_path, dst)
        print(f"  ✓  {cls:<55} {len(imgs):>6,} images")

    print(f"\n  ✅  Dataset merged → {output_dir}")
    print(f"  Next: python models/dataset_setup.py --stats {output_dir}")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AgroSage — Dataset Setup & Merge Utility"
    )
    subparsers = parser.add_subparsers(dest="command")

    # stats sub-command
    p_stats = subparsers.add_parser("stats", help="Show dataset statistics")
    p_stats.add_argument("dir", help="Path to dataset directory")

    # merge sub-command
    p_merge = subparsers.add_parser("merge", help="Merge multiple datasets")
    p_merge.add_argument("--sources", nargs="+", required=True,
                         help="Source dataset directories")
    p_merge.add_argument("--output", required=True,
                         help="Output directory (dataset/raw)")
    p_merge.add_argument("--cap", type=int, default=None,
                         help="Max images per class (e.g. 2000)")
    p_merge.add_argument("--dry-run", action="store_true",
                         help="Show what would be copied without actually copying")

    # Also support positional --stats for backwards compat
    parser.add_argument("--stats", metavar="DIR",
                        help="Show statistics for a dataset directory")
    parser.add_argument("--merge", action="store_true",
                        help="Merge mode (requires --sources and --output)")
    parser.add_argument("--sources", nargs="+")
    parser.add_argument("--output")
    parser.add_argument("--cap", type=int)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    # Handle both sub-command and flat-flag styles
    if args.command == "stats" or args.stats:
        d = args.dir if args.command == "stats" else args.stats
        print_stats(d)
    elif args.command == "merge" or args.merge:
        sources = (args.sources if args.command == "merge"
                   else getattr(args, "sources", None))
        output  = (args.output  if args.command == "merge"
                   else getattr(args, "output",  None))
        cap     = (args.cap     if args.command == "merge"
                   else getattr(args, "cap",     None))
        dry     = (args.dry_run if args.command == "merge"
                   else getattr(args, "dry_run", False))
        if not sources or not output:
            parser.error("--merge requires --sources and --output")
        merge_datasets(sources, output, cap=cap, dry_run=dry)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
