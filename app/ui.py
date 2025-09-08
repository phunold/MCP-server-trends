import streamlit as st
import pandas as pd
from pathlib import Path
from app.common import RUNS_DIR, read_jsonl

st.set_page_config(page_title="MCP Server Trends", layout="wide")
st.title("MCP Server Trends")

# Load latest run (if any)
runs = sorted([p for p in RUNS_DIR.glob("*") if p.is_dir()], reverse=True)
if not runs:
    st.info("No runs yet. Execute jobs/scan_wellknown.py to generate data.")
else:
    latest = runs[0]
    scan_file = latest / "scan_results.jsonl"
    rows = list(read_jsonl(scan_file)) if scan_file.exists() else []
    df = pd.DataFrame(rows)

    # KPIs
    total = len(df)
    hits = len(df[(df["status"] == 200) & (df["has_manifest"] == True)]) if total else 0
    https_hits = len(df[(df["status"] == 200) & (df["has_manifest"] == True) & df["url"].str.startswith("https://")]) if total else 0
    anon = df["exposure_flags"].dropna().apply(lambda x: "anonymous_access" in x).sum() if total else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Domains scanned", total)
    k2.metric("Manifests found", hits)
    k3.metric("HTTPS manifests", https_hits)
    k4.metric("Anonymous access", anon)

    st.subheader(f"Latest run: {latest.name}")
    st.dataframe(df[["domain","status","url","auth","exposure_flags","bytes"]].head(500))
