from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from jarvis.app.lifecycle import run_forever, run_once


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="jarvis")
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--once", action="store_true", help="Boot, health-check and clean shutdown.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.once:
            result = asyncio.run(run_once(args.data_dir))
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            asyncio.run(run_forever(args.data_dir))
    except KeyboardInterrupt:
        print("\nShutdown requested.")


if __name__ == "__main__":
    main()
