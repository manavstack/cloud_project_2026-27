"""
add_datasets.py
================
HAND-OFF SPEC FOR AN AI CODING AGENT (e.g. Claude Code)
--------------------------------------------------------
See project brief embedded in the file header in the user's prompt.

This script provides a registry of public datasets and implements
idempotent downloaders and basic adapters that convert raw files into
the project's common schema (one row per building per 15-min interval).

Usage examples:
    python add_datasets.py --dataset bdg2 --out data/processed/bdg2.parquet
    python add_datasets.py --dataset all  --out data/processed/

This file is intentionally conservative: adapters provide helpful
errors when raw files are not found and otherwise return a valid
empty DataFrame with the expected columns so downstream scripts can
be wired up early in the workflow.
"""

import argparse
import gzip
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

try:
    import requests
except Exception:
    requests = None

try:
    import boto3
    import botocore
except Exception:
    boto3 = None
    botocore = None

DATA_ROOT = Path("data")
RAW_DIR = DATA_ROOT / "raw"
PROCESSED_DIR = DATA_ROOT / "processed"


@dataclass
class DatasetSpec:
    key: str
    name: str
    category: str
    source_url: str
    download_method: str
    auth_required: bool
    local_raw_dir: str
    notes: str
    downloader: Optional[Callable] = field(default=None, repr=False)
    adapter: Optional[Callable] = field(default=None, repr=False)


def _spec_registry():
    # Minimal registry mirroring the handoff spec in the prompt.
    return {
        "bdg2": DatasetSpec(
            key="bdg2",
            name="Building Data Genome Project 2",
            category="building_load",
            source_url="https://github.com/buds-lab/the-building-data-genome-project",
            download_method="git_clone",
            auth_required=False,
            local_raw_dir="bdg2",
            notes="See upstream repo for CSV files per building.",
            downloader=lambda dest: _todo_git_clone(
                "https://github.com/buds-lab/the-building-data-genome-project", dest
            ),
            adapter=lambda raw_dir, n_buildings=8: _todo_adapt_bdg2(raw_dir, n_buildings),
        ),
        "nasa_power": DatasetSpec(
            key="nasa_power",
            name="NASA POWER",
            category="weather",
            source_url="https://power.larc.nasa.gov/docs/services/api/",
            download_method="http",
            auth_required=False,
            local_raw_dir="nasa_power",
            notes="REST API for hourly weather by lat/lon.",
            downloader=lambda dest: _todo_nasa_power_fetch(dest),
            adapter=lambda raw_dir, **_: _todo_adapt_weather(raw_dir),
        ),
    }


# -------------------- DOWNLOAD HELPERS --------------------

def _exists_and_nonempty(p: Path) -> bool:
    return p.exists() and any(p.iterdir())


def _todo_git_clone(repo_url: str, dest: Path):
    dest = Path(dest)
    if _exists_and_nonempty(dest):
        print(f"SKIP git clone: {dest} already exists and non-empty")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning {repo_url} -> {dest}")
    subprocess.run(["git", "clone", "--depth", "1", repo_url, str(dest)], check=False)


def _todo_kaggle_download(competition_slug: str, dest: Path):
    dest = Path(dest)
    if _exists_and_nonempty(dest):
        print(f"SKIP kaggle download: {dest} already exists and non-empty")
        return
    try:
        from shutil import which as shutil_which
    except Exception:
        shutil_which = lambda name: None
    if not shutil_which("kaggle"):
        raise RuntimeError("kaggle CLI not found; install via pip install kaggle and add ~/.kaggle/kaggle.json")
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Kaggle competition {competition_slug} -> {dest}")
    subprocess.run(["kaggle", "competitions", "download", "-c", competition_slug, "-p", str(dest)], check=False)
    # try to unzip any archives
    for z in dest.glob("*.zip"):
        try:
            import zipfile

            with zipfile.ZipFile(z, "r") as zf:
                zf.extractall(dest)
        except Exception:
            pass


def _todo_s3_public_download(s3_prefix: str, dest: Path, max_files: int = 200):
    dest = Path(dest)
    if _exists_and_nonempty(dest):
        print(f"SKIP s3 download: {dest} already exists and non-empty")
        return
    if boto3 is None or botocore is None:
        raise RuntimeError("boto3/botocore not available; install boto3 to fetch public S3 data")
    # parse s3://bucket/prefix
    assert s3_prefix.startswith("s3://"), "s3_prefix must start with s3://"
    _, rest = s3_prefix.split("s3://", 1)
    parts = rest.split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""

    client = boto3.client("s3", config=botocore.client.Config(signature_version=botocore.UNSIGNED))
    dest.mkdir(parents=True, exist_ok=True)
    paginator = client.get_paginator("list_objects_v2")
    downloaded = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            target = dest / Path(key).name
            if target.exists():
                continue
            print(f"Downloading s3://{bucket}/{key} -> {target}")
            client.download_file(bucket, key, str(target))
            downloaded += 1
            if downloaded >= max_files:
                return


def _todo_nasa_power_fetch(dest: Path, lat: float = 12.97, lon: float = 79.16, start: str = None, end: str = None):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "weather_raw.json"
    if out.exists():
        print(f"SKIP NASA POWER: {out} already exists")
        return
    if requests is None:
        raise RuntimeError("requests not available; please pip install requests")
    # If start/end aren't provided, default to the last 30 days (YYYYMMDD)
    from datetime import datetime, timedelta

    if start is None or end is None:
        today = datetime.utcnow().date()
        end_dt = today
        start_dt = today - timedelta(days=30)
        start = start or start_dt.strftime("%Y%m%d")
        end = end or end_dt.strftime("%Y%m%d")

    base = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    params = {
        "community": "RE",
        "parameters": "T2M,RH2M",
        "longitude": lon,
        "latitude": lat,
        "start": start,
        "end": end,
        "format": "JSON",
    }
    print(f"Fetching NASA POWER for lat={lat}, lon={lon}, start={start}, end={end}")
    r = requests.get(base, params=params, timeout=30)
    r.raise_for_status()
    out.write_text(r.text)
    print(f"Wrote {out}")


def _todo_openei_fetch(dest: Path, utility_query: str = "Tamil Nadu"):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "tariff_raw.json"
    if out.exists():
        print(f"SKIP OpenEI: {out} already exists")
        return
    api_key = os.environ.get("OPENEI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENEI_API_KEY not set in environment; register at openei.org and set it before running")
    if requests is None:
        raise RuntimeError("requests not available; please pip install requests")
    url = "https://api.openei.org/utility_rates"
    params = {"api_key": api_key, "search": utility_query, "format": "json"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    out.write_text(r.text)
    print(f"Wrote {out}")


# -------------------- ADAPTERS --------------------

COMMON_COLUMNS = [
    "building_id",
    "timestamp",
    "power_kw",
    "outdoor_temp",
    "humidity",
    "occupancy",
    "is_holiday",
]


def _empty_common_df() -> pd.DataFrame:
    return pd.DataFrame(columns=COMMON_COLUMNS)


def _todo_adapt_bdg2(raw_dir: Path, n_buildings: int) -> pd.DataFrame:
    raw_dir = Path(raw_dir)
    # Try to find any meter CSVs in raw_dir
    csvs = list(raw_dir.rglob("*.csv"))
    if not csvs:
        print(f"[bdg2] no CSVs found in {raw_dir} — returning empty schema DataFrame")
        return _empty_common_df()

    # This adapter intentionally provides a best-effort lightweight parse:
    # - find a file that looks like a meter reading and load a time series
    # - produce building_id values bldg_00.. based on files found (up to n_buildings)
    dfs = []
    picked = csvs[:n_buildings]
    for i, f in enumerate(picked):
        try:
            df = pd.read_csv(f, parse_dates=True)
        except Exception:
            continue
        # attempt to find a timestamp and a power column
        possible_ts = [c for c in df.columns if "date" in c.lower() or "timestamp" in c.lower()]
        possible_power = [c for c in df.columns if "meter" in c.lower() or "power" in c.lower() or "energy" in c.lower()]
        if not possible_ts or not possible_power:
            continue
        ts_col = possible_ts[0]
        p_col = possible_power[0]
        df["timestamp"] = pd.to_datetime(df[ts_col])
        # normalize to 15-min by resampling
        tmp = df.set_index("timestamp")[p_col].resample("15T").interpolate()
        out = pd.DataFrame({
            "building_id": f"bldg_{i:02d}",
            "timestamp": tmp.index.astype(str),
            "power_kw": tmp.values,
            "outdoor_temp": None,
            "humidity": None,
            "occupancy": None,
            "is_holiday": 0,
        })
        dfs.append(out)

    if not dfs:
        return _empty_common_df()
    return pd.concat(dfs, ignore_index=True)


def _todo_adapt_weather(raw_dir: Path) -> pd.DataFrame:
    raw_dir = Path(raw_dir)
    j = raw_dir / "weather_raw.json"
    if not j.exists():
        print(f"[nasa_power] {j} not found — returning empty weather table")
        return pd.DataFrame(columns=["timestamp", "outdoor_temp", "humidity"])
    txt = j.read_text()
    try:
        data = json.loads(txt)
    except Exception:
        print(f"[nasa_power] failed to parse {j}; returning empty table")
        return pd.DataFrame(columns=["timestamp", "outdoor_temp", "humidity"])
    # The NASA POWER JSON has a 'properties' -> 'parameter' structure for hourly data
    try:
        params = data["properties"]["parameter"]
        # T2M and RH2M
        t2m = params.get("T2M")
        rh2m = params.get("RH2M")
        # keys are date strings like 'YYYYMMDDHH'
        if not t2m:
            return pd.DataFrame(columns=["timestamp", "outdoor_temp", "humidity"])
        timestamps = list(t2m.keys())
        rows = []
        for ts in timestamps:
            rows.append({
                "timestamp": ts,
                "outdoor_temp": t2m.get(ts),
                "humidity": rh2m.get(ts) if rh2m else None,
            })
        return pd.DataFrame(rows)
    except Exception:
        print(f"[nasa_power] unexpected JSON layout; returning empty table")
        return pd.DataFrame(columns=["timestamp", "outdoor_temp", "humidity"])


# -------------------- ORCHESTRATION --------------------


def run_dataset(spec: DatasetSpec, out_dir: Path, n_buildings: int = 8):
    raw_dir = RAW_DIR / spec.local_raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    if spec.auth_required:
        print(f"[{spec.key}] NOTE: requires credentials -- see notes below before running.")
    print(f"[{spec.key}] {spec.notes}\n")

    print(f"[{spec.key}] downloading from {spec.source_url} ...")
    if spec.downloader:
        spec.downloader(raw_dir)
    else:
        print(f"[{spec.key}] no downloader implemented; skipping download")

    print(f"[{spec.key}] adapting to common schema ...")
    if spec.adapter:
        df = spec.adapter(raw_dir, n_buildings=n_buildings)
    else:
        df = _empty_common_df()

    out_path = out_dir / f"{spec.key}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"[{spec.key}] wrote {len(df):,} rows -> {out_path}")
    return out_path


def main():
    registry = _spec_registry()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", choices=list(registry.keys()) + ["all"], default="all",
        help="Which dataset to fetch + adapt. 'all' runs every entry in the registry."
    )
    parser.add_argument(
        "--out", type=Path, default=PROCESSED_DIR,
        help="Output directory for processed parquet files."
    )
    parser.add_argument(
        "--n-buildings", type=int, default=8,
        help="Number of buildings to select as federated clients (building_load datasets only)."
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Print the full dataset registry (name, category, auth requirements) and exit."
    )
    args = parser.parse_args()

    if args.list:
        print(json.dumps(
            {k: {"name": v.name, "category": v.category,
                 "auth_required": v.auth_required, "source_url": v.source_url}
             for k, v in registry.items()},
            indent=2
        ))
        return

    targets = list(registry.values()) if args.dataset == "all" else [registry[args.dataset]]

    for spec in targets:
        try:
            run_dataset(spec, args.out, n_buildings=args.n_buildings)
        except NotImplementedError as e:
            print(f"[{spec.key}] SKIPPED - not yet implemented: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
