import streamlit as st, altair as alt, pandas as pd
from lib.data import load_scans

st.set_page_config(page_title="Scan Diagnostics · MCP Server Trends", page_icon="🧪", layout="wide")
st.title("Scan Diagnostics (Aggregated)")

df = load_scans()
if df.empty:
    st.info("No data found.")
    st.stop()

# HTTP status distribution (aggregated)
st.subheader("HTTP status distribution")
if "status" in df.columns:
    s = df["status"].fillna(-1).astype(int).value_counts().reset_index()
    s.columns = ["status","count"]
    chart = alt.Chart(s).mark_bar().encode(
        x=alt.X("status:N", sort="-y"),
        y="count:Q",
        tooltip=["status","count"]
    ).properties(height=280)
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(s.sort_values("count", ascending=False), use_container_width=True)

# Latency distributions (aggregated)
st.subheader("Latency (TTFB / Total)")
lat_cols = [c for c in ["ttfb_ms","total_ms"] if c in df.columns]
melted = df.melt(value_vars=lat_cols, var_name="metric", value_name="ms").dropna()
if not melted.empty:
    box = alt.Chart(melted).mark_boxplot().encode(
        x=alt.X("metric:N", title="Metric"),
        y=alt.Y("ms:Q", title="Milliseconds"),
        tooltip=["metric","ms"]
    ).properties(height=300)
    st.altair_chart(box, use_container_width=True)

# Attempts per day (aggregated)
st.subheader("Attempts per day")
if "run_date" in df.columns:
    per_day = df.groupby("run_date").size().reset_index(name="attempts")
    st.bar_chart(per_day.set_index("run_date"))
