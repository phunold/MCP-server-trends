# MCP Server Trends — Project Context (Tranco + Registry + Exposure Risk + Streamlit UI)

## 🎯 Role & Objective

**Purpose**  
Measure and track public adoption of the **Model Context Protocol (MCP)** by scanning popular domains for `/.well-known/mcp.json` (and alternates like `/.well-known/mcp/manifest.json`), collecting results, and visualizing **statistics, exposure risks, and trends over time**.

**Mission**
Deliver a reproducible, low-maintenance pipeline that:

1. Selects top domains from **[Tranco](https://tranco-list.eu/)** and seeds additional targets from the **[MCP Registry](https://github.com/modelcontextprotocol/registry)**.  
2. Probes for MCP discovery data at `/.well-known/mcp.json` and alternates.  
3. Parses & normalizes any manifests found.  
4. Stores time-stamped results in structured datasets.  
5. Produces adoption graphs, exposure risk metrics, and dashboards.  

**Intended Outcomes**  

* A reliable **adoption baseline** for “top-X” domains.  
* **Exposure risk classification** of detected MCP servers.  
* **Time-series** charts (adoption overtime, TLD distribution, etc.).  
* **Reusable artifacts** (JSONL/CSV) for external analysis.  
* An optional **Streamlit UI** to interactively explore scan data.  

---

## Project Overview

**What the project does**  

* Pulls a fresh **Tranco** ranking and selects the **top N** domains.  
* **Seeds** additional targets from the **MCP Registry** (e.g., server hostnames and example deployments).  
* Probes `https://<domain>/.well-known/mcp.json` (and alternates).  
* Validates and parses any JSON manifest present.  
* Captures exposure-relevant fields (auth, tool capabilities, server type).  
* Appends one record per `(domain, run_timestamp)` to a dataset.  
* Aggregates adoption and **exposure risk metrics**.  
* Provides a **Streamlit dashboard** for interactive filtering, searching, and visualization.  

**Target users**  

* Security researchers monitoring protocol adoption.  
* Standards watchers tracking MCP ecosystem maturity.  
* Tooling/IDE vendors evaluating integration opportunities.  
* OSS community members seeking reproducible, open adoption data.  

**Main value**  
A transparent **scan → detect → classify → store → visualize** loop for MCP adoption and security posture.

---

## Key Features

1. **Domain Acquisition (Tranco)** — pull latest ranking, snapshot the list per run.  
2. **Registry Seeding (MCP Registry)** — optionally fetch known MCP server entries as seed targets; record registry version and retrieval date.  
3. **Well-Known Probe** — request `/.well-known/mcp.json` (HTTPS first, follow redirects, www canonicalization, timeouts, retries, backoff).  
4. **Manifest Parsing & Normalization** — validate JSON, capture security-relevant fields (auth required, transport, tool list).  
5. **Exposure Risk Classification** — heuristics such as:  
   * Anonymous access permitted.  
   * Dangerous tools exposed (filesystem write, network execution).  
   * No transport security (TLS issues).  
6. **Time-Series Storage** — append JSONL/CSV with run timestamp.  
7. **Metrics & Graphs** — adoption %, auth distribution, risky tool prevalence, overtime charts.  
8. **Reproducibility** — record Tranco list ID, **registry snapshot ID/date**, scan version, config.  
9. **UI (Streamlit)** — lightweight dashboard for exploring adoption metrics, filtering results, and visualizing exposure risk interactively.  
10. **(Optional) Enrichment** — [Certificate Transparency](https://certificate.transparency.dev/) subdomain discovery for additional probes.  

---

## 🛠 Technical Details

**Stack**  

* **Language:** Python  
* **Data:** JSONL for raw runs; CSV/Parquet for summaries  
* **Viz:** matplotlib for static charts; HTML/Markdown reports  
* **UI:** [Streamlit](https://streamlit.io/) for interactive dashboards  
* **Scheduling:** Manual → CI (GitHub Actions) for automation  

**Folder layout**  

`/src/
    acquire_tranco.py
    acquire_registry.py
    scan_wellknown.py
    parse_manifest.py
    classify_exposure.py
    metrics.py
    report.py
    dashboard.py
    enrich_ct.py
/data/
    runs/<YYYY-MM-DD>/
        domains_tranco_topN.txt
        registry_seeds.jsonl
        scan_results.jsonl
        summaries/
        adoption_daily.csv
/reports/
    <YYYY-MM-DD>/index.html
/tests/
/docs/`

**Data records — examples**  

*`registry_seeds.jsonl`*:

```json
{
  "run_ts": "2025-09-06T00:00:00Z",
  "registry_snapshot_id": "2025-09-06",
  "name": "Example Server",
  "homepage": "https://example.com",
  "target": "example.com",
  "notes": ["seeded-from-registry"]
}
```

*`scan_results.jsonl`*:

```json
{
  "run_ts": "2025-09-06T00:00:00Z",
  "seed_source": "tranco|registry",
  "domain": "example.com",
  "url": "https://example.com/.well-known/mcp.json",
  "status": 200,
  "has_manifest": true,
  "exposure_flags": ["anonymous_access", "dangerous_tools"],
  "auth": "none",
  "tls_grade": "B",
  "manifest_sample": {
    "name": "Example MCP",
    "version": "1.0.0",
    "capabilities": ["fs.read", "fs.write"]
  },
  "notes": []
}
```

## Project Scope & Boundaries

**In scope**  

* Scanning top-N Tranco domains and registry-seeded hosts for MCP manifests.
* Parsing JSON and classifying exposure risk.
* Time-series aggregation and static reporting.
* Optional Streamlit UI for exploring stored results.

**Out-of-scope (initially)**

* Deep crawling beyond the well-known path.
* Authenticated or private endpoints.
* Fully interactive dashboards with databases (beyond Streamlit).

**Constraints**

* Discovery conventions are evolving (mcp.json vs. manifest.json).
* Tranco includes parked domains; expect timeouts/TLS errors.
* Registry entries may be self-reported and not always production domains—treat seeds as hints, not ground truth.
* CT enrichment optional and subject to ToS/rate limits.


## Usage Examples

**Daily scan combining Tranco + Registry seeds**
```bash
python -m mcp_trends scan \
  --tranco-top 10000 \
  --seed-from registry \
  --registry-url https://github.com/modelcontextprotocol/registry/raw/main/registry.json \
  --out data/runs/2025-09-06/
```

**Generate reports**
```bash
python -m mcp_trends report --from data/runs/ --to reports/
```

**Launch interactive dashboard**

```bash
streamlit run src/dashboard.py
```

## Demo Data

To quickly try the Streamlit app without running a full scan, generate a small demo dataset (uses test fixtures and adds a few synthetic rows):

```bash
# Option A: via Makefile
make demo-data

# Option B: direct script usage (overwrites optional)
python jobs/init_demo_data.py --out-dir data/runs/$(date -u +%F) [--overwrite]

# Then launch the app
streamlit run app/Home.py
```

## Roadmap & Future Improvements

* Spec awareness — support alternate discovery paths.
* Risk taxonomy — enrich risk classification with academic research.
* Automation — scheduled GitHub Actions + GitHub Pages reports.
* Analytics — geo/TLD breakdowns, server capability taxonomy.
* UI (Streamlit) — add filters (by auth, exposure risk, TLS grade), charts, and export options.

## Contacts & References

* Repository: MCP Server Trends: [Repo](https://github.com/phunold/MCP-server-trends)
* Tranco List: https://tranco-list.eu/
* MCP Registry (GitHub): https://github.com/modelcontextprotocol/registry
* MCP Spec (GitHub): https://github.com/modelcontextprotocol/specification
* RFC 8615 Well-Known URIs: https://www.rfc-editor.org/rfc/rfc8615
* Certificate Transparency: https://certificate.transparency.dev/
* Streamlit: https://streamlit.io/
* SSL Labs (report inspiration): https://www.ssllabs.com/ssltest/
* Notes for ChatGPT usage
* Treat this file as canonical project context focused on Project #1.
* Core outputs: adoption + exposure risk from Tranco + Registry seeds.
* Provide both static artifacts (JSONL/CSV/HTML) and an optional Streamlit UI.
