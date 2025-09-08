"""
Aggregate simple adoption + exposure metrics and write CSV summaries.

Usage:
  python -m metrics --runs-dir data/runs --out-csv data/summaries/adoption_daily.csv
"""
from __future__ import annotations
import argparse, csv, pathlib, re
from collections import Counter, defaultdict
from common import RUNS_DIR, SUMMARIES_DIR, read_jsonl, ensure_dir

def iter_scan_results(runs_dir: pathlib.Path):
    for day_dir in sorted(runs_dir.glob("*")):
        f = day_dir / "scan_results.jsonl"
        if f.exists():
            for row in read_jsonl(f):
                yield day_dir.name, row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", type=pathlib.Path, default=RUNS_DIR)
    ap.add_argument("--out-csv", type=pathlib.Path, default=SUMMARIES_DIR / "adoption_daily.csv")
    args = ap.parse_args()

    daily = defaultdict(lambda: {"total": 0, "hits": 0, "https_hits": 0, "anon": 0, "dangerous": 0})
    for day, r in iter_scan_results(args.runs_dir):
        d = daily[day]
        d["total"] += 1
        if r.get("status") == 200 and r.get("has_manifest"):
            d["hits"] += 1
            if str(r.get("url","")).startswith("https://"):
                d["https_hits"] += 1
            flags = set(r.get("exposure_flags") or [])
            if "anonymous_access" in flags:
                d["anon"] += 1
            if "dangerous_tools" in flags:
                d["dangerous"] += 1

    ensure_dir(args.out_csv.parent)
    with args.out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date","total_scanned","manifests_found","https_manifests","anonymous_access","dangerous_tools"])
        for day in sorted(daily.keys()):
            d = daily[day]
            w.writerow([day, d["total"], d["hits"], d["https_hits"], d["anon"], d["dangerous"]])
    print(f"Wrote summary → {args.out_csv}")

if __name__ == "__main__":
    main()

