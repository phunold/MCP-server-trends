from __future__ import annotations
import argparse
import datetime as dt
import json
import pathlib
from typing import Iterable


ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
RUNS_DIR = ROOT / "data" / "runs"


def ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def read_jsonl(path: pathlib.Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def write_jsonl(path: pathlib.Path, rows: Iterable[dict]) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def today_str() -> str:
    # Use timezone-aware UTC date
    return dt.datetime.now(dt.UTC).date().isoformat()


def main():
    ap = argparse.ArgumentParser(description="Initialize small demo dataset for the Streamlit app.")
    ap.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=RUNS_DIR / today_str(),
        help="Destination run directory (default: data/runs/<today>)",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing scan_results.jsonl if present.",
    )
    args = ap.parse_args()

    out_file = args.out_dir / "scan_results.jsonl"
    if out_file.exists() and not args.overwrite:
        print(f"Exists: {out_file} (use --overwrite to replace)")
        return

    # Seed rows from small test fixtures (covers: detected, blocked, timeouts)
    rows: list[dict] = []
    notion_path = TESTS_DIR / "test-200-notion.com.jsonl"
    docker_path = TESTS_DIR / "test-403-docker.io.jsonl"

    if notion_path.exists():
        rows.extend(read_jsonl(notion_path))
    if docker_path.exists():
        rows.extend(read_jsonl(docker_path))

    # Ensure we also include a simple 404/absent example for variety
    # Timezone-aware UTC timestamp with trailing Z for consistency
    now_iso = dt.datetime.now(dt.UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows.append({
        "run_ts": now_iso,
        "seed_source": "demo",
        "domain": "example.com",
        "url": "https://example.com/.well-known/mcp.json",
        "status": 404,
        "has_manifest": False,
        "notes": ["demo-absent"],
    })

    # Write out
    write_jsonl(out_file, rows)
    print(f"Demo data written: {out_file} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
