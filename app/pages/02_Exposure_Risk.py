import streamlit as st, altair as alt
from lib.data import load_scans, exposure_counts

st.set_page_config(page_title="Exposure Risk · MCP Server Trends", page_icon="🛡️", layout="wide")
st.title("Exposure Risk (Aggregated)")

df = load_scans()
if df.empty:
    st.info("No data found.")
    st.stop()

# Exposure flags distribution
st.subheader("Exposure flags")
flags_df = exposure_counts(df)
if flags_df.empty:
    st.write("No exposure flags recorded yet.")
else:
    chart = (
        alt.Chart(flags_df)
        .mark_bar()
        .encode(x=alt.X("flag:N", sort="-y", title="Flag"),
                y=alt.Y("count:Q", title="Count"),
                tooltip=["flag","count"])
        .properties(height=320)
    )
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(flags_df, use_container_width=True)

# Auth distribution (aggregated)
st.subheader("Auth modes")
if "auth" in df.columns:
    auth_df = df[df.get("has_manifest", False) == True]["auth"].value_counts().reset_index()
    auth_df.columns = ["auth","count"]
    if not auth_df.empty:
        pie = (
            alt.Chart(auth_df)
            .mark_arc()
            .encode(theta="count:Q", color="auth:N", tooltip=["auth","count"])
            .properties(height=300)
        )
        st.altair_chart(pie, use_container_width=True)
        st.dataframe(auth_df, use_container_width=True)
    else:
        st.write("No auth data yet.")
else:
    st.write("No auth column found.")
