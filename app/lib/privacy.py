from __future__ import annotations
import hashlib, os
import streamlit as st
import pandas as pd

AGG_ONLY = bool(st.secrets.get("privacy", {}).get("PUBLIC_AGGREGATES_ONLY", True))
_SALT = st.secrets.get("privacy", {}).get("SALT") or os.environ.get("MCP_TRENDS_SALT") or os.urandom(16).hex()

# Columns we will never expose
SENSITIVE_COLUMNS = {
    "domain", "url", "manifest_sample", "homepage", "target",
    "icon", "endpoint", "ip", "hostname", "emails",
    "etag", "last_modified", "sha256"
}

def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    # Drop known identifiers
    out = out.drop(columns=[c for c in out.columns if c in SENSITIVE_COLUMNS], errors="ignore")
    # Scrub any string that might contain a URL or domain
    for c in out.columns:
        if out[c].dtype == "object":
            out[c] = out[c].astype(str)
            out[c] = out[c].str.replace(r"(https?://\S+)", "[redacted]", regex=True)
            out[c] = out[c].str.replace(r"\b([A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b", "[redacted]", regex=True)
    return out

def aggregates_banner():
    if AGG_ONLY:
        st.sidebar.warning("Aggregates-only mode: identifiers are redacted.")
