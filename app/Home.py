import streamlit as st
from lib.privacy import aggregates_banner

st.set_page_config(
    page_title="MCP Server Trends",
    page_icon="📡",
    layout="wide"
)

st.title("MCP Server Trends")

# Show aggregates-only warning banner
aggregates_banner()

st.info(
    "This dashboard shows **aggregated research data only**. "
    "Identifiers (domains, IPs, URLs, manifests) are **never** displayed or exported."
)

st.markdown("""
### 📊 Pages
- **Overview** → KPIs + detection trend + TLD distribution  
- **Exposure Risk** → exposure flag and auth charts (aggregated)  
- **Time Series** → adoption over time + outcome comparison  
- **Scan Diagnostics** → HTTP status + latency distributions (aggregated)

---

🔍 **Purpose**: Measure and track adoption of the Model Context Protocol (MCP) by scanning top-ranked domains + registry seeds.  
Only trends and aggregated metrics are shared here — no individual domains or identifiers.
""")