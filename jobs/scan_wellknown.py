"""
Asynchronously probe domains for MCP manifests at well-known paths, then
classify exposure flags and emit scan_results.jsonl.

Usage:
  python -m scan_wellknown \
    --domains data/runs/2025-09-06/domains_tranco_topN.txt --seed-source tranco \
    --out data/runs/2025-09-06/scan_results.jsonl

  # Or from registry seeds:
  cut -d',' -f1 data/runs/2025-09-06/registry_seeds.jsonl | jq -r .target | sort -u > /tmp/registry_targets.txt
  python -m scan_wellknown --domains /tmp/registry_targets.txt --seed-source registry --out ...
"""
from __future__ import annotations
import argparse, asyncio, json, pathlib, re, sys, typing as t
import httpx

from app.common import (ScanResult, ensure_dir, now_iso, sha256_bytes, write_jsonl,
                    DEFAULT_TIMEOUT, USER_AGENT)

WELLKNOWN_PATHS = [
    "/.well-known/mcp.json",
    "/.well-known/mcp/manifest.json",  # alternate seen in the wild
]

DANGEROUS_TOOL_HINTS = re.compile(r"(fs\.write|file\.write|exec|shell|subprocess|network\.(get|post)|http\.)", re.I)

def choose_auth_hint(manifest: dict | None) -> str | None:
    if not manifest:
        return None
    # heuristics: look for top-level fields or metadata
    auth = manifest.get("auth") or manifest.get("authentication") or {}
    if isinstance(auth, dict):
        methods = ",".join(auth.keys()).lower()
        if "oauth" in methods:
            return "oauth2"
        if "api" in methods or "api_key" in methods or "token" in methods:
            return "api_key"
    return "none" if manifest else "unknown"

def classify_exposure(manifest: dict | None, status: int, scheme: str) -> list[str]:
    flags: list[str] = []
    if status == 200 and manifest is not None:
        flags.append("anonymous_access")
    # Dangerous tools hint
    tools = manifest.get("tools") if isinstance(manifest, dict) else None
    tool_text = json.dumps(tools) if tools is not None else ""
    if DANGEROUS_TOOL_HINTS.search(tool_text):
        flags.append("dangerous_tools")
    # TLS presence (very rough)
    if scheme != "https":
        flags.append("no_tls")
    return flags or None

async def fetch_one(client: httpx.AsyncClient, base: str) -> tuple[str, dict | None, int, dict, bytes | None, str]:
    # returns (url_used, manifest, status, headers, content, scheme)
    for path in WELLKNOWN_PATHS:
        url = f"https://{base}{path}"
        try:
            r = await client.get(url, follow_redirects=True, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": USER_AGENT})
            content = r.content if (r.status_code == 200 and "application/json" in r.headers.get("content-type","")) else None
            manifest = json.loads(content.decode("utf-8")) if content else None
            if r.status_code == 200:
                return (str(r.url), manifest, r.status_code, dict(r.headers), content, "https")
        except Exception:
            pass
        # try http only if https failed entirely
        url = f"http://{base}{path}"
        try:
            r = await client.get(url, follow_redirects=True, timeout=DEFAULT_TIMEOUT, headers={"User-Agent": USER_AGENT})
            content = r.content if (r.status_code == 200 and "application/json" in r.headers.get("content-type","")) else None
            manifest = json.loads(content.decode("utf-8")) if content else None
            if r.status_code == 200:
                return (str(r.url), manifest, r.status_code, dict(r.headers), content, "http")
        except Exception:
            pass
    return ("", None, 0, {}, None, "https")

async def worker(domains: list[str], seed_source: str, out_path: pathlib.Path, run_ts: str, concurrency: int = 100):
    ensure_dir(out_path.parent)
    sem = asyncio.Semaphore(concurrency)
    rows: list[dict] = []

    async with httpx.AsyncClient(http2=True) as client:
        async def scan(domain: str):
            async with sem:
                url_used, manifest, status, headers, content, scheme = await fetch_one(client, domain.strip())
                sr = ScanResult(
                    run_ts=run_ts,
                    seed_source=seed_source,
                    domain=domain.strip(),
                    url=url_used or f"https://{domain}/.well-known/mcp.json",
                    status=int(status or 0),
                    has_manifest=bool(manifest),
                    bytes=(len(content) if content else None),
                    etag=headers.get("etag"),
                    last_modified=headers.get("last-modified"),
                    sha256=(sha256_bytes(content) if content else None),
                    auth=choose_auth_hint(manifest),
                    tls_grade=("A" if scheme == "https" else "F"),
                    exposure_flags=classify_exposure(manifest, int(status or 0), scheme),
                    manifest_sample=(manifest if manifest else None),
                    notes=[]
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
    ap.add_argument("--seed-source", choices=["tranco", "registry"], required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--concurrency", type=int, default=100)
    args = ap.parse_args()

    run_ts = now_iso()
    domains = load_domains(args.domains)
    asyncio.run(worker(domains, args.seed_source, args.out, run_ts, args.concurrency))
    print(f"Scan finished → {args.out}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[scan_wellknown] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
