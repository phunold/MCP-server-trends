"""
Deep scanner for discovered MCP remote servers.

Reads scan_results.jsonl from a run directory, extracts MCP endpoints from
manifest samples, and performs safe JSON-RPC probes (no tool execution).

Outputs an aggregated JSONL file with per-endpoint posture:
- auth/anonymous acceptance
- JSON-RPC availability
- counts of tools/resources/prompts
- heuristic dangerous tool flags (names only)

Usage:
  uv run jobs/scan_remotes.py \
    --run-dir data/runs/2025-09-06 \
    --out data/runs/2025-09-06/remote_scan.jsonl \
    [--concurrency 64]

Notes:
- Only makes read-only JSON-RPC calls like tools/list, prompts/list, resources/list.
- Does not call tools/call or any potentially mutating operations.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import pathlib
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from app.common import (
    ensure_dir,
    now_iso,
    write_jsonl,
    HTTPX_LIMITS,
    HTTPX_TIMEOUT,
    USER_AGENT,
)


# Heuristic set of dangerous tool name fragments (lowercased matching)
DANGEROUS_PATTERNS = [
    r"\bwrite\b", r"\bdelete\b", r"\bremove\b", r"\bchmod\b", r"\bchown\b",
    r"shell", r"exec", r"spawn", r"process", r"sudo", r"system",
    r"http", r"fetch", r"curl", r"request",
    r"docker", r"kube", r"kubectl",
    r"git", r"ssh",
]
_DANGEROUS_RE = re.compile("|".join(DANGEROUS_PATTERNS), re.IGNORECASE)


def load_scan_rows(scan_file: pathlib.Path) -> Iterable[Dict[str, Any]]:
    if not scan_file.exists():
        return []
    with scan_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def extract_endpoints(row: Dict[str, Any]) -> List[str]:
    """Extract likely MCP JSON-RPC endpoints from a manifest sample.

    Supports a few common shapes:
    - { "endpoint": "https://..." }
    - { "endpoints": ["https://...", ...] }
    - { "remotes": [{"endpoint": "..."} or {"url": "..."}] }
    """
    eps: List[str] = []
    m = row.get("manifest_sample") or {}
    if not isinstance(m, dict):
        return eps

    ep = m.get("endpoint")
    if isinstance(ep, str) and ep:
        eps.append(ep)

    epl = m.get("endpoints")
    if isinstance(epl, list):
        for e in epl:
            if isinstance(e, str) and e:
                eps.append(e)

    remotes = m.get("remotes")
    if isinstance(remotes, list):
        for r in remotes:
            if isinstance(r, dict):
                for k in ("endpoint", "url", "url_direct"):
                    val = r.get(k)
                    if isinstance(val, str) and val:
                        eps.append(val)

    # De-duplicate while preserving order
    seen = set()
    out: List[str] = []
    for e in eps:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def classify_tools(tools: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
    names: List[str] = []
    for t in tools or []:
        name = t.get("name") if isinstance(t, dict) else None
        if isinstance(name, str):
            names.append(name)
    danger = [n for n in names if _DANGEROUS_RE.search(n or "")]
    return len(names), len(danger), danger[:20]  # cap list for size/privacy


async def jsonrpc_post(
    client: httpx.AsyncClient,
    url: str,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    request_id: int = 1,
) -> Tuple[int, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Make a JSON-RPC POST request. Returns (status_code, result, error)."""
    body = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        body["params"] = params
    try:
        r = await client.post(url, json=body)
        status = r.status_code
        data = None
        try:
            data = r.json()
        except Exception:
            return status, None, {"code": None, "message": "non-json response"}
        if isinstance(data, dict):
            if "error" in data:
                err = data.get("error")
                return status, None, err if isinstance(err, dict) else {"code": None, "message": str(err)}
            return status, data.get("result"), None
        return status, None, {"code": None, "message": "unexpected payload"}
    except httpx.HTTPStatusError as e:
        return e.response.status_code if e.response else 0, None, {"code": None, "message": str(e)}
    except httpx.RequestError as e:
        return 0, None, {"code": None, "message": str(e)}


async def probe_endpoint(client: httpx.AsyncClient, domain: str, endpoint: str, run_ts: str) -> Dict[str, Any]:
    """Probe a single endpoint with safe JSON-RPC calls."""
    # First call: tools/list — best signal for capabilities
    status, result, error = await jsonrpc_post(client, endpoint, "tools/list", params={})

    accepts_anonymous = False
    rpc_ok = False
    tools_count = 0
    dangerous_count = 0
    dangerous_names: List[str] = []
    prompts_count = None
    resources_count = None

    if status == 200 and result is not None:
        rpc_ok = True
        tools = result.get("tools") if isinstance(result, dict) else None
        if isinstance(tools, list):
            tools_count, dangerous_count, dangerous_names = classify_tools(tools)
        accepts_anonymous = True
    elif status in (401, 403):
        accepts_anonymous = False
    elif status == 200 and error is not None:
        # JSON-RPC error payload but HTTP OK – could be method not found or auth error
        code = (error or {}).get("code")
        if code in (401, 403, -32001):  # heuristic unauthorized codes
            accepts_anonymous = False

    # Opportunistic follow-up probes if first call succeeded anonymously
    if rpc_ok and accepts_anonymous:
        # prompts/list
        s2, res2, _ = await jsonrpc_post(client, endpoint, "prompts/list", params={})
        if s2 == 200 and isinstance(res2, dict):
            prompts = res2.get("prompts")
            if isinstance(prompts, list):
                prompts_count = len(prompts)
        # resources/list
        s3, res3, _ = await jsonrpc_post(client, endpoint, "resources/list", params={})
        if s3 == 200 and isinstance(res3, dict):
            resources = res3.get("resources")
            if isinstance(resources, list):
                resources_count = len(resources)

    row = {
        "run_ts": run_ts,
        "domain": domain,
        "endpoint": endpoint,
        "transport": "http-jsonrpc",
        "status_http": status,
        "accepts_anonymous": accepts_anonymous,
        "rpc_ok": rpc_ok,
        "tools_count": tools_count,
        "dangerous_tools_count": dangerous_count,
        "dangerous_tool_names": dangerous_names,
        "prompts_count": prompts_count,
        "resources_count": resources_count,
        "rpc_error": error,
    }
    return row


async def worker(tasks: List[Tuple[str, str, str]], out_path: pathlib.Path, concurrency: int = 64) -> None:
    ensure_dir(out_path.parent)
    sem = asyncio.Semaphore(concurrency)
    rows: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(
        limits=HTTPX_LIMITS,
        transport=httpx.AsyncHTTPTransport(retries=0),
        http2=False,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        follow_redirects=True,
        timeout=HTTPX_TIMEOUT,
    ) as client:

        async def run_probe(domain: str, endpoint: str, run_ts: str):
            async with sem:
                row = await probe_endpoint(client, domain, endpoint, run_ts)
                rows.append(row)

        coros = [asyncio.create_task(run_probe(d, e, ts)) for (d, e, ts) in tasks]
        for i in range(0, len(coros), 500):
            chunk = coros[i : i + 500]
            await asyncio.gather(*chunk)
            write_jsonl(out_path, rows)
            rows.clear()


def build_tasks(run_dir: pathlib.Path) -> List[Tuple[str, str, str]]:
    scan_file = run_dir / "scan_results.jsonl"
    tasks: List[Tuple[str, str, str]] = []
    for r in load_scan_rows(scan_file):
        if not (r.get("status") == 200 and r.get("has_manifest")):
            continue
        domain = r.get("domain") or ""
        run_ts = r.get("run_ts") or now_iso()
        for ep in extract_endpoints(r):
            if isinstance(ep, str) and ep.startswith("http"):
                tasks.append((domain, ep, run_ts))
    return tasks


def main():
    ap = argparse.ArgumentParser(description="Probe MCP remote servers via JSON-RPC.")
    ap.add_argument("--run-dir", type=pathlib.Path, required=True, help="Run directory containing scan_results.jsonl")
    ap.add_argument("--out", type=pathlib.Path, help="Output JSONL path (default: <run-dir>/remote_scan.jsonl)")
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    out = args.out or (args.run_dir / "remote_scan.jsonl")
    tasks = build_tasks(args.run_dir)
    logging.info(f"Prepared {len(tasks)} endpoint probes from {args.run_dir}")

    if not tasks:
        logging.info("No endpoints to probe. Exiting.")
        return

    asyncio.run(worker(tasks, out, args.concurrency))
    logging.info(f"Wrote remote scan results → {out}")


if __name__ == "__main__":
    main()

