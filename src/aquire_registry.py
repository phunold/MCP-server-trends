"""
Fetch MCP registry seeds from PulseMCP REST API and write a JSONL file.

Usage:
  uv run src/acquire_registry.py \
    --out data/runs/2025-09-06/registry_seeds.jsonl

Optional:
  uv run src/acquire_registry.py \
    --query "image" \
    --count-per-page 5000 \
    --out data/runs/2025-09-06/registry_seeds.jsonl
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys
import time
from urllib.parse import urlparse

import httpx
from common import ensure_dir, now_iso, write_jsonl

BASE_URL = "https://api.pulsemcp.com/v0beta/servers"
UA = "mcp-server-trends/0.1 (+https://github.com/phunold/MCP-server-trends)"

def hostname_from_url(u: str | None) -> str | None:
    if not u:
        return None
    try:
        netloc = urlparse(u).netloc
        return netloc.split("@")[-1].split(":")[0] if netloc else None
    except Exception:
        return None

def iter_servers(query: str | None, count_per_page: int):
    """Yield server objects across pages using the 'next' URL."""
    params = {"count_per_page": count_per_page}
    if query:
        params["query"] = query

    next_url = BASE_URL
    with httpx.Client(follow_redirects=True, headers={"User-Agent": UA}, timeout=20.0) as client:
        while next_url:
            r = client.get(next_url, params=params if next_url == BASE_URL else None)
            r.raise_for_status()
            data = r.json()
            for s in data.get("servers", []):
                yield s
            next_url = data.get("next")
            # be polite vs. rate limits (20 rps / 200 rpm documented)
            time.sleep(0.05)

def main():
    ap = argparse.ArgumentParser(description="Acquire registry seeds from PulseMCP API.")
    ap.add_argument("--out", type=pathlib.Path, required=True, help="Output JSONL file for seeds.")
    ap.add_argument("--query", type=str, default=None, help="Optional search query.")
    ap.add_argument("--count-per-page", type=int, default=5000, help="Results per page (max 5000).")
    ap.add_argument("--snapshot-id", type=str, default=None, help="e.g., YYYY-MM-DD; defaults to run date.")
    args = ap.parse_args()

    ensure_dir(args.out.parent)
    snapshot_id = args.snapshot_id or now_iso()[:10]
    run_ts = now_iso()

    rows = []
    try:
        for s in iter_servers(args.query, args.count_per_page):
            # Primary site/host
            primary_host = hostname_from_url(s.get("url")) or hostname_from_url(s.get("external_url"))

            # Remote endpoints may include direct connect URLs; extract hostnames
            remotes = s.get("remotes") or []
            remote_hosts = []
            for r in remotes:
                h = hostname_from_url(r.get("url_direct"))
                if h:
                    remote_hosts.append((h, r.get("transport"), r.get("authentication_method"), r.get("cost"), r.get("url_direct")))

            # skip if no remote_hosts found
            if not remote_hosts:
                continue

            # Build rows: one per discovered target (primary + remotes)
            base_row = {
            #    "run_ts": run_ts,
            #    "registry_source": "pulsemcp",
            #    "registry_snapshot_id": snapshot_id,
                "name": s.get("name") or "",
                "homepage": s.get("url") or s.get("external_url") or "",
                #"notes": ["seeded-from-pulsemcp"],
            }
            #if primary_host:
            #    rows.append({**base_row, "target": primary_host, "remote_transport": None,
            #                 "remote_auth": None, "remote_cost": None, "notes": "PRIMARY HOST"})

            for host, transport, auth, cost, url_direct in remote_hosts:
                rows.append({**base_row, "target": host, "remote_transport": transport,
                             "remote_auth": auth, "remote_cost": cost, "url_direct": url_direct, "notes": "REMOTE ENDPOINT"})
    except httpx.HTTPError as e:
        print(f"[acquire_registry] HTTP error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[acquire_registry] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    write_jsonl(args.out, rows)
    print(f"Wrote {len(rows)} seeds → {args.out}")

if __name__ == "__main__":
    main()
