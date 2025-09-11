import streamlit as st, altair as alt
from lib.data import load_scans, adoption_by_date

st.set_page_config(page_title="Overview · MCP Server Trends", page_icon="📊", layout="wide")
st.title("Adoption Overview")

df = load_scans()
if df.empty:
    st.info("No data found. Put JSONL files under data/runs/YYYY-MM-DD/scan_results.jsonl")
    st.stop()

# KPIs (safe)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total scan rows", f"{len(df):,}")
with col2:
    st.metric("Detections (has_manifest)", f"{(df.get('has_manifest', False) == True).sum():,}")
with col3:
    st.metric("Run days", f"{df['run_date'].nunique() if 'run_date' in df else 0:,}")
with col4:
    st.metric("Outcomes tracked", f"{df['outcome'].nunique() if 'outcome' in df else 0:,}")

# Trend
st.subheader("Detections over time")
daily = adoption_by_date(df)
if daily.empty:
    st.write("No detections yet.")
else:
    chart = (
        alt.Chart(daily)
        .mark_line(point=True)
        .encode(x=alt.X("run_date:T", title="Date"),
                y=alt.Y("detections:Q", title="Detected servers"),
                tooltip=["run_date:T","detections:Q"])
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)

# TLD distribution (aggregated)
st.subheader("TLD distribution (detections only)")
if "tld" in df.columns:
    tld_df = (df[(df.get("has_manifest", False) == True) & df["tld"].notna()]
              .groupby("tld").size().reset_index(name="count")
              .sort_values("count", ascending=False).head(20))
    if not tld_df.empty:
        bar = (
            alt.Chart(tld_df)
            .mark_bar()
            .encode(x=alt.X("tld:N", sort="-y", title="TLD"),
                    y=alt.Y("count:Q", title="Detected servers"),
                    tooltip=["tld","count"])
            .properties(height=280)
        )
        st.altair_chart(bar, use_container_width=True)
        st.dataframe(tld_df, use_container_width=True)
    else:
        st.write("No TLD data yet.")
