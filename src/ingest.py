import argparse
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from .config import (
    SAMPLE_RAW_DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DIR,
    HOURLY_PATH,
    DAILY_CITY_PATH,
)
from .preprocessing import preprocess_hourly
from .aggregations import aggregate_daily_city


def _discover_csv_files(root_dir: Path) -> List[Path]:
    """Recursively discover all CSV files under a root directory."""
    csv_files: List[Path] = []
    if not root_dir.exists():
        return csv_files

    for p in root_dir.rglob("*.csv"):
        if p.is_file():
            csv_files.append(p)
    return sorted(csv_files)


def _load_raw_from_dir(root_dir: Path) -> pd.DataFrame:
    """
    Load all CSV files under given directory and concatenate them into one DataFrame.

    This assumes all CSVs share the same schema (column names).
    """
    csv_files = _discover_csv_files(root_dir)
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found under directory: {root_dir}")

    frames = []
    for path in csv_files:
        try:
            df = pd.read_csv(path)
            frames.append(df)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Failed to read {path}: {exc}")

    if not frames:
        raise RuntimeError(f"All CSV files under {root_dir} failed to read.")

    combined = pd.concat(frames, ignore_index=True)
    return combined


def build_and_save_datasets(use_raw: bool = False, overwrite: bool = True) -> None:
    """
    Main entry: build and save hourly and daily_city datasets.

    Parameters
    ----------
    use_raw : bool
        If True, ingest from data/raw/ (full dataset);
        otherwise ingest from data/sample_raw/ (demo subset).
    overwrite : bool
        If False and target Parquet files already exist, skip rebuilding.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not overwrite and HOURLY_PATH.exists() and DAILY_CITY_PATH.exists():
        print(f"[INFO] Processed data already exist, skipping rebuild. use_raw={use_raw}")
        return

    source_dir = RAW_DATA_DIR if use_raw else SAMPLE_RAW_DATA_DIR
    print(f"[INFO] Loading raw CSV data from: {source_dir}")  # noqa: T201

    raw_df = _load_raw_from_dir(source_dir)
    print(f"[INFO] Raw rows: {len(raw_df)}")  # noqa: T201

    hourly_df = preprocess_hourly(raw_df)
    print(f"[INFO] Preprocessed rows: {len(hourly_df)}")  # noqa: T201

    daily_city_df = aggregate_daily_city(hourly_df)
    print(f"[INFO] City-day rows: {len(daily_city_df)}")  # noqa: T201

    # Write Parquet outputs
    hourly_df.to_parquet(HOURLY_PATH, index=False)
    daily_city_df.to_parquet(DAILY_CITY_PATH, index=False)

    print(f"[OK] Generated {HOURLY_PATH} and {DAILY_CITY_PATH}")  # noqa: T201


def cli_main(argv: Iterable[str] | None = None) -> None:
    """Command-line entry point for ingestion pipeline."""
    parser = argparse.ArgumentParser(
        description="Air quality ingestion & preprocessing & aggregation script",
    )
    parser.add_argument(
        "--use-raw",
        action="store_true",
        help="Use data/raw/ directory instead of sample_raw/.",
    )
    parser.add_argument(
        "--use-sample",
        action="store_true",
        help="Force using data/sample_raw/ (mutually exclusive with --use-raw).",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Do not overwrite existing Parquet files if they already exist.",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.use_raw and args.use_sample:
        parser.error("--use-raw and --use-sample cannot be used together.")

    use_raw = args.use_raw and not args.use_sample
    overwrite = not args.no_overwrite

    build_and_save_datasets(use_raw=use_raw, overwrite=overwrite)


if __name__ == "__main__":
    cli_main()
