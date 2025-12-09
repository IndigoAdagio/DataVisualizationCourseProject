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
    """
    递归扫描 root_dir 下所有的 .csv 文件。

    目录结构一般为：
    root_dir/YYYY-MM-DD/YYYY-MM-DDTHH.csv
    """
    csv_files: List[Path] = []
    if not root_dir.exists():
        return csv_files

    for p in root_dir.rglob("*.csv"):
        if p.is_file():
            csv_files.append(p)
    return sorted(csv_files)


def _load_raw_from_dir(root_dir: Path) -> pd.DataFrame:
    """
    从给定目录递归读取所有 CSV，并拼接为长表。

    为了简化示例，假设所有 CSV 拥有一致的列名结构。
    """
    csv_files = _discover_csv_files(root_dir)
    if not csv_files:
        raise FileNotFoundError(f"在目录 {root_dir} 下未找到任何 CSV 文件。")

    frames = []
    for path in csv_files:
        try:
            df = pd.read_csv(path)
            frames.append(df)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] 读取 {path} 失败: {exc}")

    if not frames:
        raise RuntimeError(f"在目录 {root_dir} 下的 CSV 均读取失败。")

    combined = pd.concat(frames, ignore_index=True)
    return combined


def build_and_save_datasets(use_raw: bool = False, overwrite: bool = True) -> None:
    """
    主入口函数：构建并保存 hourly / daily_city 两个数据集。

    参数
    ------
    use_raw : bool
        为 True 时，从 data/raw/ 读取真实数据；
        为 False 时，从 data/sample_raw/ 读取示例数据。
    overwrite : bool
        为 False 时，如果目标 Parquet 已存在则不重复构建。
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not overwrite and HOURLY_PATH.exists() and DAILY_CITY_PATH.exists():
        print("[INFO] 处理后数据已存在，跳过重建。 use_raw=%s" % use_raw)
        return

    source_dir = RAW_DATA_DIR if use_raw else SAMPLE_RAW_DATA_DIR
    print(f"[INFO] 正在从 {source_dir} 读取原始 CSV 数据……")  # noqa: T201

    raw_df = _load_raw_from_dir(source_dir)
    print(f"[INFO] 原始数据行数：{len(raw_df)}")  # noqa: T201

    hourly_df = preprocess_hourly(raw_df)
    print(f"[INFO] 预处理后数据行数：{len(hourly_df)}")  # noqa: T201

    daily_city_df = aggregate_daily_city(hourly_df)
    print(f"[INFO] 城市-日聚合数据行数：{len(daily_city_df)}")  # noqa: T201

    # 写出 Parquet（需要 pyarrow 或 fastparquet 支持）
    hourly_df.to_parquet(HOURLY_PATH, index=False)
    daily_city_df.to_parquet(DAILY_CITY_PATH, index=False)

    print(f"[OK] 已生成 {HOURLY_PATH} 和 {DAILY_CITY_PATH}")  # noqa: T201


def cli_main(argv: Iterable[str] | None = None) -> None:
    """命令行入口，方便单独运行 ingest 脚本。"""
    parser = argparse.ArgumentParser(
        description="空气质量数据导入 & 预处理 & 聚合脚本",
    )
    parser.add_argument(
        "--use-raw",
        action="store_true",
        help="使用 data/raw/ 目录下的真实完整数据，而不是示例数据 sample_raw/。",        )
    parser.add_argument(
        "--use-sample",
        action="store_true",
        help="强制使用示例数据 data/sample_raw/（与 --use-raw 互斥）。",        )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="若目标 Parquet 已存在则不覆盖。",        )

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.use_raw and args.use_sample:
        parser.error("--use-raw 与 --use-sample 不能同时使用。")

    use_raw = args.use_raw and not args.use_sample
    overwrite = not args.no_overwrite

    build_and_save_datasets(use_raw=use_raw, overwrite=overwrite)


if __name__ == "__main__":
    cli_main()
