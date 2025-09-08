"""
Acquire Tranco domains using the official SDK.

Examples:
  uv run src/acquire_tranco.py --top 10000 --out data/runs/2025-09-06/domains_tranco_topN.txt
"""

from __future__ import annotations
import argparse
import logging
import pathlib
from typing import List
import sys

from tranco import Tranco
from app.common import ensure_dir

def get_tranco_domains(top_n: int) -> List[str]:
    """
    Returns domains using Tranco SDK.
    """
    t = Tranco(cache=True, cache_dir=".tranco")
    lst = t.list()
    return lst.top(top_n)

def main():
    ap = argparse.ArgumentParser(description="Fetch Tranco domains via SDK.")
    ap.add_argument("--top", type=int, required=True, help="How many top domains to select.")
    ap.add_argument("--out", type=pathlib.Path, required=True, help="Output file (one domain per line).")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    ensure_dir(args.out.parent)
 
    logging.info("Fetching Tranco list (SDK)…")
    try:
        domains = get_tranco_domains(args.top)
    except Exception as e:
        logging.error(f"Failed to load Tranco list: {e}")
        sys.exit(1)

    with args.out.open("w", encoding="utf-8") as f:
        for d in domains:
            f.write(d.strip() + "\n")

    logging.info(f"Wrote {len(domains)} domains → {args.out}")

if __name__ == "__main__":
    main()
