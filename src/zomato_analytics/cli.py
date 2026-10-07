"""Command-line entry point.

zomato-analytics run  --input data/raw/zomato.csv --out reports
zomato-analytics demo --out reports            # synthetic data, no download needed
zomato-analytics sample --out data/raw/sample.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import config, pipeline, sample_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zomato-analytics",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run the pipeline on the real Kaggle extract")
    run_p.add_argument("--input", type=Path, default=config.DEFAULT_RAW_FILE)
    run_p.add_argument("--out", type=Path, default=config.REPORTS_DIR)
    run_p.add_argument("--no-charts", action="store_true")

    demo_p = sub.add_parser("demo", help="Generate synthetic data and run the pipeline on it")
    demo_p.add_argument("--out", type=Path, default=config.REPORTS_DIR)
    demo_p.add_argument("--rows", type=int, default=3000)
    demo_p.add_argument("--seed", type=int, default=42)

    sample_p = sub.add_parser("sample", help="Write a synthetic raw-format CSV")
    sample_p.add_argument("--out", type=Path, default=config.RAW_DIR / "zomato_sample.csv")
    sample_p.add_argument("--rows", type=int, default=3000)
    sample_p.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    if args.command == "sample":
        path = sample_data.write_sample(args.out, args.rows, args.seed)
        print(f"Wrote {path}")
    elif args.command == "demo":
        path = sample_data.write_sample(config.RAW_DIR / "zomato_sample.csv", args.rows, args.seed)
        pipeline.run(path, args.out, is_sample=True)
        print(f"Demo outputs written to {args.out} (synthetic data, illustrative only)")
    else:
        pipeline.run(args.input, args.out, make_charts=not args.no_charts)
        print(f"Outputs written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
