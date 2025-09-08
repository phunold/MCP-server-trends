Got it — here’s a **single, static project description** you can drop into your ChatGPT “Project” folder (e.g., `PROJECT_CONTEXT.md`). It’s self-contained context for the MCP Server Trends repo.

---

# MCP Server Trends — Project Context

## Checklist (what this file covers)

* Role & Objective
* Project Overview
* Key Features
* Technical Details
* Project Scope & Boundaries
* Usage Examples
* Roadmap & Future Improvements
* Contacts & References

---

## 🎯 Role & Objective

**Purpose**
Measure and track public adoption of the **Model Context Protocol (MCP)** by scanning popular domains for `/.well-known/mcp.json`, collecting results, and visualizing **statistics and trends over time**.

**Mission**
Deliver a reproducible, low-maintenance pipeline that:

1. selects top domains from **Tranco**,
2. probes for MCP discovery data,
3. parses & normalizes any manifests found,
4. stores time-stamped results, and
5. produces graphs and summary metrics.

**Intended Outcomes**

* A reliable **adoption baseline** for “top-X” domains.
* **Time-series** charts (overtime adoption, distribution by TLD, etc.).
* **Reusable artifacts** (JSONL/CSV) for external analysis and comparisons.

**Alignment check:** All statements support scanning, measuring, and explaining MCP adoption clearly and reproducibly.

---

## 🌐 Project Overview

**What the project does**

* Pulls a fresh **Tranco** ranking and selects the **top N** domains.
* Probes `https://<domain>/.well-known/mcp.json` (with sane retries/redirects).
* Validates and parses any JSON manifest present.
* Appends one record per `(domain, run_timestamp)` to a dataset.
* Aggregates and **visualizes adoption metrics**.

**Target users**

* Researchers and standards watchers tracking protocol adoption.
* Tooling/IDE vendors evaluating MCP ecosystem maturity.
* OSS community members who want reproducible, open data.

**Main value**
A simple, transparent **scan → detect → parse → store → visualize** loop for MCP adoption.

**Alignment check:** High-level summary is consistent with the purpose and outcomes.

---

## ⚙️ Key Features

1. **Domain Acquisition (Tranco)** — pull the latest ranking, snapshot the exact list used per run.
2. **Well-Known Probe** — request `/.well-known/mcp.json` (HTTPS first, follow redirects, optional `www` canonicalization, per-host timeouts, backoff, and rate limiting).
3. **Manifest Parsing & Normalization** — validate JSON; capture status code, size, ETag/Last-Modified (if any), and selected manifest fields (e.g., `name`, `version`, `capabilities`).
4. **Time-Series Storage** — append to JSONL (and optionally Parquet/CSV summaries) with a **run timestamp** to enable trend analysis.
5. **Metrics & Graphs** — adoption %, status distributions, TLD breakdowns, attribute histograms, and **overtime** charts.
6. **Reproducibility** — record Tranco list ID/date, tool version, and config used.
7. **(Optional) Enrichment** — certificate transparency–based subdomain discovery for follow-up probes on positives.

**Alignment check:** Each feature contributes directly to accurate measurement and clear reporting.

---

## 🛠 Technical Details

**Stack**

* **Language:** Python
* **Data:** JSONL for raw runs; CSV/Parquet for summaries (optional)
* **Viz:** Static charts (e.g., matplotlib), HTML/Markdown reports
* **Scheduling:** Local/manual to start; CI (GitHub Actions) later

**Suggested folder layout (guidance)**

```
/src/
  acquire_tranco.py
  scan_wellknown.py
  parse_manifest.py
  metrics.py
  report.py
  enrich_ct.py           # optional
/data/
  runs/<YYYY-MM-DD>/
    domains_tranco_topN.txt
    scan_results.jsonl
  summaries/
    adoption_daily.csv
/reports/
  <YYYY-MM-DD>/index.html
/tests/
/docs/
```

**Data record (JSONL) — example shape**

```json
{
  "run_ts": "2025-09-05T00:00:00Z",
  "domain": "example.com",
  "url": "https://example.com/.well-known/mcp.json",
  "status": 200,
  "has_manifest": true,
  "bytes": 1234,
  "etag": "W/\"abc...\"",
  "last_modified": "Fri, 05 Sep 2025 00:00:00 GMT",
  "sha256": "…",
  "manifest_sample": {
    "name": "Example MCP",
    "version": "1.0.0",
    "capabilities": ["..."]
  },
  "notes": []
}
```

**Alignment check:** Technical choices emphasize simplicity, reproducibility, and portability.

---

## 📌 Project Scope & Boundaries

**In-scope**

* Scanning **top-N Tranco** domains for `/.well-known/mcp.json`.
* Robust HTTP probing (redirects, HTTPS preference, timeouts/backoff).
* JSON validation and light schema normalization.
* Time-series aggregation and **static** reporting.

**Out-of-scope (initially)**

* Deep crawling beyond the well-known path.
* Authenticated or private endpoints.
* Fully interactive dashboards with databases.
* Formal sector classification beyond simple TLD grouping.

**Constraints / Known Limitations**

* Discovery conventions may evolve; this project treats `/.well-known/mcp.json` as the primary signal and can add alternates behind flags.
* Tranco includes a mix of domains (some parked/unresponsive); expect timeouts/TLS issues.
* External enrichment sources (e.g., CT) may have rate limits/ToS—use responsibly.

**Alignment check:** Boundaries keep the MVP focused while acknowledging ecosystem changes.

---

## 👤 Usage Examples

**Example 1 — Daily top-10k scan**

```
python -m mcp_trends scan --tranco-top 10000 --out data/runs/2025-09-05/
# Produces: scan_results.jsonl, adoption summary, and /reports/ with charts
```

**Example 2 — Rebuild reports from existing data**

```
python -m mcp_trends report --from data/runs/ --to reports/
# Reads prior JSONL runs, emits updated CSVs and static charts
```

**Alignment check:** Examples demonstrate typical, end-to-end usage succinctly.

---

## 🗺 Roadmap & Future Improvements

* **Spec awareness:** feature-flag alternate discovery paths if standardized.
* **Data pipeline:** Parquet outputs, monthly roll-ups, integrity checksums.
* **Automation:** GitHub Actions to schedule scans and publish GitHub Pages.
* **Analytics:** Geo/TLD breakdowns, manifest capability taxonomy, stability checks.
* **UI (stretch):** lightweight client-side dashboard reading static JSON.

**Alignment check:** Roadmap extends capability without bloating the core scanner.

---

## 📞 Contacts & References

* **Repository:** [https://github.com/phunold/MCP-server-trends](https://github.com/phunold/MCP-server-trends)
* **Primary contact:** \[Your name / handle / email]
* **External references (context only):**

  * Tranco ranking (research-oriented top sites)
  * MCP documentation/spec site
  * RFC 8615 (Well-Known URIs)
  * Certificate Transparency resources (for optional enrichment)

**Alignment check:** Points to the repo and stable references without depending on live links for core understanding.

---

**Notes for ChatGPT usage**

* Treat this file as canonical **project context**.
* Prefer **concise, reproducible steps** and **static artifacts** (JSONL/CSV/HTML).
* When suggesting changes, keep them **MVP-friendly** and avoid scope creep unless explicitly requested.
