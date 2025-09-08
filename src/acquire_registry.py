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
import logging
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

def iter_servers():
    """Yield server objects across pages using the 'next' URL."""
    
    # log BASE_URL
    logging.info(f"PulseMCP API base url: {BASE_URL}")
    next_url = BASE_URL

    with httpx.Client(follow_redirects=True, headers={"User-Agent": UA}, timeout=20.0) as client:
        while next_url:
            logging.info(f"Fetching {next_url}…")
            r = client.get(next_url)
            r.raise_for_status()
            data = r.json()
            for s in data.get("servers", []):
                yield s
            next_url = data.get("next")
            # be polite vs. rate limits (20 rps / 200 rpm documented)
            time.sleep(0.05)
    
        logging.info(f"Finished iter_servers: no more pages.")

def main():
    ap = argparse.ArgumentParser(description="Acquire registry seeds from PulseMCP API.")
    ap.add_argument("--out", type=pathlib.Path, required=True, help="Output JSONL file for seeds.")
    args = ap.parse_args()

    # format logging to include timestamp
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    ensure_dir(args.out.parent)
    logging.info(f"Fetching registry seeds from PulseMCP API...")
    rows = []
    count_primary = 0
    count_remotes = 0

    for s in iter_servers():
        # log s for debugging
        logging.debug(f"Server entry: {json.dumps(s, indent=2)}")

        # Remote endpoints may include direct connect URLs; extract hostnames
        remotes = s.get("remotes") or []
        remote_hosts = []
        for r in remotes:
            h = hostname_from_url(r.get("url_direct"))
            if h:
                remote_hosts.append((h, r.get("transport"), r.get("authentication_method"), r.get("cost"), r.get("url_direct")))

        # calculate some stats for fun
        count_primary += 1
        count_remotes += len(remote_hosts)

        # skip if no remote_hosts found
        if not remote_hosts:
            continue

        # Build rows: one per discovered remote mcp host
        base_row = {
            "name": s.get("name") or "",
            "homepage": s.get("url") or s.get("external_url") or "",
        }
        for host, transport, auth, cost, url_direct in remote_hosts:
            rows.append({
                **base_row,
                "target": host,
                "remote_transport": transport,
                "remote_auth": auth,
                "remote_cost": cost,
                "url_direct": url_direct,
                "fetched_at": now_iso(),
            })

    # finally, write out the results and log some stats
    write_jsonl(args.out, rows)
    logging.info(f"Fetched {len(rows)} seeds from {count_primary} primary hosts and {count_remotes} remote endpoints. Output written to: {args.out}")
    
if __name__ == "__main__":
    main()
