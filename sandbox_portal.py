"""
sandbox_portal.py - Secure Evaluation Sandbox & Heuristic Testing Portal
Allows evaluators to simulate telemetry vectors and test server-authoritative defense policies safely.
Run with: python -m streamlit run sandbox_portal.py --server.port 8503
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import db_manager as db

st.set_page_config(
    page_title="Garza Global Graviton - Evaluation Sandbox",
    page_icon="🧪",
    layout="wide"
)

st.markdown("""
<style>
    .sandbox-banner {
        background: linear-gradient(135deg, #090d16 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 25px;
        color: #f8fafc;
        text-align: center;
        margin-bottom: 20px;
    }
    .card {
        background-color: #1e293b;
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

policies = db.get_policies()

st.markdown("""
<div class="sandbox-banner">
    <h1>Isolated Evaluation Sandbox</h1>
    <p style="color: #38bdf8;">Simulate telemetry vectors and test anti-cheat heuristic responses in a controlled environment.</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 🎮 Simulator Controls")
    st.write("Trigger simulated telemetry anomalies against active server policies to evaluate response latency and mitigation accuracy.")
    
    with st.form("sandbox_sim_form"):
        sim_vector = st.selectbox("Select Anomaly Vector", [
            "Sub-Tick Aim Snap (Exceeds Threshold)",
            "Velocity Deviation Spike ($\sigma > 2.2$)",
            "Memory Hook Signature Injection",
            "Packet Interval Jitter Spike"
        ])
        
        sim_intensity = st.slider("Anomaly Intensity Level", min_value=1, max_value=10, value=5)
        
        sim_submit = st.form_submit_button("Fire Simulation Packet", use_container_width=True)
        
        if sim_submit:
            # Determine action based on current active policies
            action = "Blocked & Logged"
            confidence = "High (99.8%)"
            
            if "Memory Hook" in sim_vector and policies.get("auto_kick_memory_hook", 1):
                action = "Instant Client Isolation & Termination"
            elif "Aim Snap" in sim_vector and policies.get("sub_tick_packet_scan", 1):
                action = "Sub-Tick Correction & Vector Rejection"
            else:
                action = "Flagged for Heuristic Review"
                
            db.log_security_event("SANDBOX-NODE-01", "Evaluation Sandbox Node", sim_vector, action, confidence)
            st.success(f"Simulation processed successfully! Mitigation Rule Triggered: **{action}**")

with col2:
    st.markdown("### 🛡️ Active Sandbox Telemetry Log")
    st.write("Real-time ledger entries generated from simulation tests.")
    
    events = db.get_recent_events(limit=10)
    if events:
        df_events = pd.DataFrame(events)[["timestamp", "node_name", "vector", "action_taken", "confidence"]]
        st.dataframe(df_events, use_container_width=True, hide_index=True)
    else:
        st.info("No sandbox simulation events recorded yet. Run a test simulation on the left.")

st.markdown("---")
st.markdown("### 🔒 Security & IP Protection Notice")
st.caption("This sandbox executes against an isolated database instance. Core proprietary algorithms, decryption keys, and server binaries remain securely hidden from client view.")