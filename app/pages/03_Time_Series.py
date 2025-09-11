import streamlit as st, altair as alt
from lib.data import load_scans, adoption_by_date

st.set_page_config(page_title="Time Series · MCP Server Trends", page_icon="📈", layout="wide")
st.title("Time Series")

df = load_scans()
if df.empty:
    st.info("No data found.")
    st.stop()

st.subheader("Daily detections")
daily = adoption_by_date(df)
if not daily.empty:
    line = (
        alt.Chart(daily)
        .mark_line(point=True)
        .encode(x=alt.X("run_date:T"), y=alt.Y("detections:Q"),
                tooltip=["run_date:T","detections:Q"])
        .properties(height=300)
    )
    st.altair_chart(line, use_container_width=True)
else:
    st.write("No detections yet.")

st.subheader("Outcome distribution by day")
if "run_date" in df.columns and "outcome" in df.columns:
    cmp = (df.groupby(["run_date","outcome"]).size()
           .reset_index(name="count"))
    if not cmp.empty:
        chart = (
            alt.Chart(cmp)
            .mark_line(point=True)
            .encode(x=alt.X("run_date:T"),
                    y=alt.Y("count:Q"),
                    color="outcome:N",
                    tooltip=["run_date:T","outcome:N","count:Q"])
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
