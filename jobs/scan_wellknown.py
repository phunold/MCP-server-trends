"""
Asynchronously probe domains for MCP manifests at well-known path.

Usage:
  python -m scan_wellknown \
    --domains data/runs/2025-09-06/domains_tranco_topN.txt \
    --out data/runs/2025-09-06/scan_results.jsonl

"""
from __future__ import annotations
import argparse, asyncio, socket, json, pathlib, sys, typing as t
import httpx
import logging
from functools import lru_cache


from app.common import (ScanResult, ensure_dir, now_iso, sha256_bytes, write_jsonl,
                    DEFAULT_TIMEOUT, USER_AGENT, HTTPX_LIMITS, HTTPX_TIMEOUT)

# check for this mcp.json file
WELLKNOWN_MCP = "/.well-known/mcp.json"
# at a later stage could check for other paths
# "/.well-known/mcp/manifest.json",  # alternate seen in the wild

# setup logging configuration
def setup_logging():
    # Define a clean format for your project
    log_format = "[%(asctime)s] %(levelname)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,      # your default level
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Silence noisy third-party libraries
    for noisy in ["httpx"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Example: only show WARNING+ from third parties
    # logging.getLogger(noisy).disabled = True  # if you want total silence

# manage DNS resolution with timeout and optional www fallback
DNS_TIMEOUT = 2.0  # seconds
DNS_CONCURRENCY = 64          # <— new, keep this modest
WWW_FALLBACK = True  # try www. if bare domain fails

async def pick_host_for_http(domain: str) -> tuple[str, list[str]]:
    """
    Return (host_used, ip_list) if resolvable. Tries apex, then www.<apex> (optional).
    Raises the last exception if neither resolves.
    """
    loop = asyncio.get_running_loop()
    host = domain.strip().lower().strip(".")

    async def _resolve(h: str) -> list[str]:
        infos = await asyncio.wait_for(
            loop.getaddrinfo(
                h, 443,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
                proto=0,
                flags=getattr(socket, "AI_ADDRCONFIG", 0),
            ),
            timeout=DNS_TIMEOUT,
        )
        return sorted({ai[4][0] for ai in infos})

    # try apex
    try:
        ips = await _resolve(host)
        return host, ips
    except Exception as e_apex:
        # optional www fallback
        if WWW_FALLBACK and not host.startswith("www."):
            try:
                www = "www." + host
                ips = await _resolve(www)
                return www, ips
            except Exception as e_www:
                # re-raise www error (more informative if it also failed)
                raise e_www
        # no www fallback or it’s disabled
        raise e_apex
    

#async def fetch_one(client: httpx.AsyncClient, base: str) -> tuple[str, dict | None, int, dict, bytes | None]:
async def fetch_one(client: httpx.AsyncClient, base: str):
    # returns (url_used, manifest, status, headers, content)

    url = f"https://{base}{WELLKNOWN_MCP}"
    
    try:
        t0 = asyncio.get_running_loop().time()
        async with client.stream("GET", url) as r:
            t_first = asyncio.get_running_loop().time()
            content_type = r.headers.get("content-type", "").lower().split(";")[0].strip()

            raw = b""
            async for chunk in r.aiter_bytes():
                raw += chunk
                if len(raw) > 131072:  # 128kiB max
                    break

            t_end = asyncio.get_running_loop().time()

            manifest = None
            if r.status_code == 200:
                body = raw.lstrip()
                looks_like_json = body[:1] in (b"{", b"[") or "json" in content_type
                if looks_like_json and raw:
                    try:
                        manifest = json.loads(raw.decode("utf-8", "replace"))
                    except json.JSONDecodeError:
                        logging.warning(f"JSONDecodeError for {url}")
                        pass
        return (
            url,
            manifest,
            r.status_code,
            dict(r.headers),
            raw if r.status_code == 200 else None, # only keep body for 200 OK
            round((t_first - t0) * 1000, 1),  # time to first byte (ttfb) in ms
            round((t_end - t0) * 1000, 1),    # total time in ms
        )
    except httpx.RequestError as e:
        logging.warning(f"RequestError for {url}: {e.args}")
        return (url, None, 0, {}, None, None, None)

async def worker(domains: list[str], out_path: pathlib.Path, run_ts: str, concurrency: int = 100):
    ensure_dir(out_path.parent)
    sem = asyncio.Semaphore(concurrency)
    dns_sem = asyncio.Semaphore(DNS_CONCURRENCY)
    rows: list[dict] = []

    async with httpx.AsyncClient(
        limits=HTTPX_LIMITS,
        transport=httpx.AsyncHTTPTransport(retries=0),
        http2=False,    # h1 is fine for one-host-per-request scans
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=HTTPX_TIMEOUT,
    ) as client:
        async def scan(domain: str):
            d = domain.strip()
            try:
                async with dns_sem:
                    host_used, ips = await pick_host_for_http(d)
            except Exception as e:
                # DNS resolution failed / write row and return to avoid HTTP fetch
                note = f"dns_error:{getattr(e, 'errno', '') or type(e).__name__}"
                sr = ScanResult(
                    run_ts=run_ts,
                    domain=d,
                    url=f"https://{d}{WELLKNOWN_MCP}",
                    status=0,
                    has_manifest=False,
                    notes=[note],
                )
                rows.append(sr.asdict())
                return
            
            # proceed with HTTP fetch
            async with sem:
                url_used, manifest, status, headers, content, ttfb_ms, total_ms = await fetch_one(client, host_used)
                sr = ScanResult(
                    run_ts=run_ts,
                    domain=d,
                    url=url_used or f"https://{host_used}{WELLKNOWN_MCP}",
                    status=int(status or 0),
                    has_manifest=bool(manifest),
                    bytes=(len(content) if content else None),
                    etag=headers.get("etag"),
                    last_modified=headers.get("last-modified"),
                    sha256=(sha256_bytes(content) if content else None),
                    ttfb_ms=ttfb_ms,
                    total_ms=total_ms,
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

    run_ts = now_iso()
    domains = load_domains(args.domains)
    logging.info(f"Starting scan of {len(domains)} domains …")

    asyncio.run(worker(domains, args.out, run_ts, args.concurrency))
    logging.info(f"Scan finished → {args.out}")

if __name__ == "__main__":
    try:
        setup_logging()
        logging.info("Starting MCP scan...")

        main()
    except Exception as e:
        logging.info(f"[scan_wellknown] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
