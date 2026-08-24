"""
portals/gaming_telemetry.py - Standalone Gaming Telemetry & Fleet Portal
Includes active node monitoring, anti-cheat security events, and system alert feeds with high-contrast styling.
Run with: python -m streamlit run portals/gaming_telemetry.py --server.port 8501
"""

import streamlit as st
import pandas as pd
import db_manager as db

st.set_page_config(page_title="Gaming Telemetry & Fleet", page_icon="⚙️", layout="wide")

# High-contrast CSS override to ensure text is fully legible on dark themes
st.markdown("""
<style>
    .card {
        background-color: #1e293b;
        border: 1px solid #38bdf8;
        padding: 20px;
        border-radius: 8px;
        color: #ffffff !important;
        margin-bottom: 15px;
    }
    p, h1, h2, h3, h4, span, label {
        color: #f8fafc !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# ⚙️ Gaming Telemetry & Fleet Control")
st.write("Independent module for live anti-cheat metrics, server-authoritative node management, and system health alerts.")

nodes = db.get_all_nodes()
events = db.get_recent_events(limit=50)
alerts = db.get_system_alerts(limit=25)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Active Fleet Nodes", value=len(nodes))
with col2:
    st.metric(label="Logged Security Events", value=len(events))
with col3:
    st.metric(label="System Alerts", value=len(alerts))

st.markdown("---")
st.subheader("Active Nodes")
if nodes:
    st.dataframe(pd.DataFrame(nodes)[["id", "name", "region", "tickrate", "status"]], use_container_width=True, hide_index=True)
else:
    st.info("No active nodes provisioned.")

st.subheader("Recent Security Events")
if events:
    st.dataframe(pd.DataFrame(events)[["timestamp", "node_name", "vector", "action_taken", "confidence"]], use_container_width=True, hide_index=True)
else:
    st.info("No security events logged.")

st.subheader("🚨 Live System Infrastructure Alerts")
if alerts:
    st.dataframe(pd.DataFrame(alerts)[["logged_at", "severity", "component", "message"]], use_container_width=True, hide_index=True)
else:
    st.success("No system infrastructure warnings or errors detected.")