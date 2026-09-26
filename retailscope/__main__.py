import argparse
import json
from pathlib import Path

from .pipeline import run
from .synthetic import generate
from .uci import run_uci


def main():
    parser = argparse.ArgumentParser(description="RetailScope retail CRM analytics")
    parser.add_argument("command", choices=["generate", "analyze", "all", "uci"], nargs="?", default="all")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--input", type=Path, help="Path to the UCI Online Retail II .xlsx workbook")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "uci":
        if not args.input:
            parser.error("uci requires --input /path/to/online_retail_II.xlsx")
        config = json.loads((root / "uci_config.json").read_text(encoding="utf-8"))
        print("[1/1] Adapting UCI data and evaluating chronological models...", flush=True)
        print(json.dumps(run_uci(root, args.input.resolve(), config), indent=2, ensure_ascii=False))
        return
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    if args.command in ["generate", "all"]:
        print("[1/2] Generating fictional retail data...", flush=True)
        generate(root, config)
    if args.command in ["analyze", "all"]:
        print("[2/2] Resolving customers, validating events and evaluating models...", flush=True)
        print(json.dumps(run(root, config), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
