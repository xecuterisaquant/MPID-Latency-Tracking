#!/usr/bin/env python3
"""Utility to tally CME ES trade events stored as Parquet files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple

import duckdb


def count_trade_rows(parquet_dir: Path) -> Tuple[int, List[Tuple[str, int]]]:
    """Return the total rows and per-file counts for all Parquets in parquet_dir."""
    if not parquet_dir.exists():
        raise FileNotFoundError(f"Directory does not exist: {parquet_dir}")

    parquet_files = sorted(parquet_dir.glob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"No Parquet files found under {parquet_dir}")

    conn = duckdb.connect()
    per_file = []
    for path in parquet_files:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(path)],
        ).fetchone()[0]
        per_file.append((path.name, row_count))

    total_rows = sum(count for _, count in per_file)
    return total_rows, per_file


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "parquet_dir",
        type=Path,
        nargs="?",
        default=Path("~/Downloads/202503 cme trade data").expanduser(),
        help="Directory containing ES trade Parquet files (default: %(default)s)",
    )
    args = parser.parse_args()

    total_rows, per_file = count_trade_rows(args.parquet_dir)

    print(f"Scanning {len(per_file)} Parquet files under {args.parquet_dir}")
    for name, count in per_file:
        print(f"  {name}: {count:,} trades")
    print(f"Total trades: {total_rows:,}")
    print(f"Average per day: {total_rows / len(per_file):,.0f}")


if __name__ == "__main__":
    main()
