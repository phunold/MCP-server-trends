"""
Emit a minimal static HTML report per run directory from scan_results.jsonl.

Usage:
  python -m report --run-dir data/runs/2025-09-06 --out reports/2025-09-06/index.html
"""
from __future__ import annotations
import argparse, html, json, pathlib
from statistics import mean
from common import ensure_dir, read_jsonl

TEMPLATE = """<!doctype html>
<html><head>
  <meta charset="utf-8"/>
  <title>MCP Server Trends — {date}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Arial, sans-serif; margin: 2rem; }}
    h1, h2 {{ margin: 0.2rem 0; }}
    .muted {{ color: #555; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #ddd; padding: 6px; font-size: 14px; }}
    th {{ background: #f5f5f5; text-align: left; }}
    code {{ background: #f6f8fa; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
<h1>MCP Server Trends</h1>
<p class="muted">Run: <b>{date}</b> — scanned: <b>{total}</b>, manifests: <b>{hits}</b>, https: <b>{https_hits}</b>, anonymous: <b>{anon}</b>, dangerous tools: <b>{dangerous}</b></p>

<h2>Sample findings (first 100)</h2>
<table>
  <thead><tr><th>Domain</th><th>Status</th><th>URL</th><th>Auth</th><th>Exposure</th><th>Bytes</th></tr></thead>
  <tbody>
    {rows}
  </tbody>
</table>

</body></html>
"""

def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    hits = sum(1 for r in rows if r.get("status")==200 and r.get("has_manifest"))
    https_hits = sum(1 for r in rows if r.get("status")==200 and r.get("has_manifest") and str(r.get("url","")).startswith("https://"))
    anon = sum(1 for r in rows if "anonymous_access" in (r.get("exposure_flags") or []))
    dangerous = sum(1 for r in rows if "dangerous_tools" in (r.get("exposure_flags") or []))
    return dict(total=total, hits=hits, https_hits=https_hits, anon=anon, dangerous=dangerous)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()

    scan_file = args.run_dir / "scan_results.jsonl"
    rows = list(read_jsonl(scan_file)) if scan_file.exists() else []
    stats = summarize(rows)

    sample = rows[:100]
    tr_rows = []
    for r in sample:
        expos = ",".join(r.get("exposure_flags") or [])
        tr_rows.append(
            f"<tr><td>{html.escape(r.get('domain',''))}</td>"
            f"<td>{r.get('status')}</td>"
            f"<td><code>{html.escape(r.get('url',''))}</code></td>"
            f"<td>{html.escape(r.get('auth') or '')}</td>"
            f"<td>{html.escape(expos)}</td>"
            f"<td>{r.get('bytes') or ''}</td></tr>"
        )

    ensure_dir(args.out.parent)
    html_out = TEMPLATE.format(date=args.run_dir.name, rows="\n".join(tr_rows), **stats)
    args.out.write_text(html_out, encoding="utf-8")
    print(f"Wrote report → {args.out}")

if __name__ == "__main__":
    main()
