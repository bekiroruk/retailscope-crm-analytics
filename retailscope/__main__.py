import argparse
import json
from pathlib import Path

from .pipeline import run
from .synthetic import generate


def main():
    parser = argparse.ArgumentParser(description="RetailScope synthetic retail analytics")
    parser.add_argument("command", choices=["generate", "analyze", "all"], nargs="?", default="all")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    if args.command in ["generate", "all"]:
        print("[1/2] Generating fictional retail data...", flush=True)
        generate(root, config)
    if args.command in ["analyze", "all"]:
        print("[2/2] Resolving customers, validating events and evaluating models...", flush=True)
        print(json.dumps(run(root, config), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
