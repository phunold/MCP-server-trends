"""
Asynchronously probe domains for MCP manifests at well-known path.

Usage:
  python -m scan_wellknown \
    --domains data/runs/2025-09-06/domains_tranco_topN.txt \
    --out data/runs/2025-09-06/scan_results.jsonl

"""
from __future__ import annotations
import argparse, asyncio, json, pathlib, sys, typing as t
import httpx
import logging

from app.common import (ScanResult, ensure_dir, now_iso, sha256_bytes, write_jsonl,
                    DEFAULT_TIMEOUT, USER_AGENT)

# check for this mcp.json file
WELLKNOWN_MCP = "/.well-known/mcp.json"
# at a later stage could check for other paths
# "/.well-known/mcp/manifest.json",  # alternate seen in the wild

async def fetch_one(client: httpx.AsyncClient, base: str) -> tuple[str, dict | None, int, dict, bytes | None]:
    # returns (url_used, manifest, status, headers, content)
    logging.info(f"Probing {base} …")
    url = f"https://{base}{WELLKNOWN_MCP}"
    try:
        r = await client.get(url, follow_redirects=True, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": USER_AGENT})
        content_type = r.headers.get("content-type", "").split(";")[0].strip().lower()
        content = r.content if (r.status_code == 200 and content_type == "application/json") else None
        manifest = json.loads(content.decode("utf-8")) if content else None
        if r.status_code == 200:
            return (url, manifest, r.status_code, r.headers, content)
    except httpx.RequestError:
        logging.debug(f"RequestError for {url}")
        pass
    except json.JSONDecodeError:
        logging.debug(f"JSONDecodeError for {url}")
        pass
    # we could try plain http here...but skipping for now
    return ("", None, 0, {}, None)

async def worker(domains: list[str], out_path: pathlib.Path, run_ts: str, concurrency: int = 100):
    ensure_dir(out_path.parent)
    sem = asyncio.Semaphore(concurrency)
    rows: list[dict] = []

    async with httpx.AsyncClient(http2=True) as client:
        async def scan(domain: str):
            async with sem:
                url_used, manifest, status, headers, content = await fetch_one(client, domain.strip())
                sr = ScanResult(
                    run_ts=run_ts,
                    domain=domain.strip(),
                    url=url_used or f"https://{domain}/.well-known/mcp.json",
                    status=int(status or 0),
                    has_manifest=bool(manifest),
                    bytes=(len(content) if content else None),
                    etag=headers.get("etag"),
                    last_modified=headers.get("last-modified"),
                    sha256=(sha256_bytes(content) if content else None),
                    manifest_sample=(manifest if manifest else None),
                    notes=["super cool ;-)"],
                )
                rows.append(sr.asdict())

        tasks = [asyncio.create_task(scan(d)) for d in domains if d.strip()]
        # periodic flush to avoid memory blow-up
        for i in range(0, len(tasks), 1000):
            chunk = tasks[i:i+1000]
            await asyncio.gather(*chunk)
            write_jsonl(out_path, rows)
            rows.clear()

def load_domains(path: pathlib.Path) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", type=pathlib.Path, required=True, help="file with one domain per line")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--concurrency", type=int, default=100)
    args = ap.parse_args()

    # setup logging severity to info
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    
    run_ts = now_iso()
    domains = load_domains(args.domains)
    logging.info(f"Starting scan of {len(domains)} domains …")

    asyncio.run(worker(domains, args.out, run_ts, args.concurrency))
    logging.info(f"Scan finished → {args.out}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.info(f"[scan_wellknown] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
