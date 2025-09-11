from __future__ import annotations
import json, pathlib, pandas as pd
import streamlit as st
from .privacy import sanitize_df

DATA_BASE = pathlib.Path(__file__).resolve().parents[1] / ".." / "data" / "runs"

@st.cache_data(show_spinner=False)
def load_scans(data_base: str | pathlib.Path = DATA_BASE, sanitized: bool = True) -> pd.DataFrame:
    base = pathlib.Path(data_base)
    if not base.exists():
        return pd.DataFrame()

    records = []
    for run_dir in sorted(base.glob("*")):
        scan_file = run_dir / "scan_results.jsonl"
        if scan_file.exists():
            with scan_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Types & derived columns
    if "run_ts" in df.columns:
        df["run_ts"] = pd.to_datetime(df["run_ts"], errors="coerce", utc=True)
        df["run_date"] = df["run_ts"].dt.date

    for c in ["status", "bytes", "ttfb_ms", "total_ms"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    for list_col in ["exposure_flags", "notes", "manifest_caps"]:
        if list_col in df.columns:
            df[list_col] = df[list_col].apply(lambda x: tuple(x) if isinstance(x, list) else ())

    # Outcome bucket
    def classify(row):
        s = row.get("status")
        has = bool(row.get("has_manifest"))
        if has and s == 200: return "detected"
        if s in (401, 402, 403): return "blocked"
        if s in (404, 410): return "absent"
        if s == 0 or pd.isna(s) or (isinstance(s, (int, float)) and s >= 500): return "error"
        return "other"
    df["outcome"] = df.apply(classify, axis=1)

    # TLD bucket (non-identifying)
    if "domain" in df.columns:
        df["tld"] = df["domain"].astype(str).str.rsplit(".", n=1).str[-1]

    if sanitized:
        df = sanitize_df(df)

    # Keep only safe columns
    keep = [c for c in df.columns if c in {
        "run_ts","run_date","seed_source","status","has_manifest","bytes","ttfb_ms","total_ms",
        "auth","tls_grade","exposure_flags","manifest_caps","outcome","tld"
    }]
    return df[keep]

# Aggregation helpers (safe)
def adoption_by_date(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "run_date" not in df.columns:
        return pd.DataFrame(columns=["run_date","detections"])
    return (df[df.get("has_manifest", False) == True]
            .groupby("run_date").size()
            .reset_index(name="detections"))

def exposure_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "exposure_flags" not in df.columns:
        return pd.DataFrame(columns=["flag","count"])
    flags = []
    for row in df["exposure_flags"]:
        for f in (row or []):
            flags.append(f)
    s = pd.Series(flags)
    if s.empty:
        return pd.DataFrame(columns=["flag","count"])
    out = s.value_counts().reset_index()
    out.columns = ["flag","count"]
    return out
