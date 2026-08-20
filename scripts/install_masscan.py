"""CLI entry point for the pinned official Masscan source installer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from laitoxx.features.network.masscan_scanner.installer import install_masscan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args()
    try:
        install_masscan(args.dest, print)
    except Exception as exc:
        print(f"[WARNING] Masscan was not installed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
