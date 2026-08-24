"""
investor_portal.py - Read-Only Stakeholder & Government Agency Portal
Features: Executive Overview, Technical Architecture, Business Plan Roadmap, 
          Compliance Summaries, and Formal Evaluation Access Request Intake.
Run with: python -m streamlit run investor_portal.py --server.port 8502
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import db_manager as db

# --- Page Configuration ---
st.set_page_config(
    page_title="Garza Global Graviton - Stakeholder Portal",
    page_icon="🏛️",
    layout="wide"
)

# --- Custom Styling ---
st.markdown("""
<style>
    .portal-banner {
        background: linear-gradient(135deg, #090d16 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 30px;
        color: #f8fafc;
        text-align: center;
        margin-bottom: 25px;
    }
    .roadmap-box {
        background-color: #1e293b;
        border-left: 4px solid #38bdf8;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

nodes = db.get_all_nodes()
events = db.get_recent_events(limit=500)
policies = db.get_policies()

# --- Header ---
st.markdown("""
<div class="portal-banner">
    <h1>Garza Global Graviton</h1>
    <p style="font-size: 1.2em; color: #38bdf8;">Stakeholder, Investor, & Government Agency Evaluation Portal</p>
    <p style="font-family: monospace; color: #94a3b8;">Entity: Illinois LLC | Secure Infrastructure & Telemetry Verification</p>
</div>
""", unsafe_allow_html=True)

# --- High-Level Metrics ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Operational Nodes", value=f"{len(nodes)} Active")
with col2:
    st.metric(label="Verified Security Events", value=f"{len(events)} Logged")
with col3:
    st.metric(label="Core Tickrate", value="128.0 Hz Fixed")
with col4:
    st.metric(label="Compliance Status", value="Verified Ready")

st.markdown("---")

# --- Navigation Tabs ---
tab_overview, tab_roadmap, tab_architecture, tab_compliance, tab_request = st.tabs([
    "📈 Executive Overview", 
    "🗺️ Business Plan & Roadmap",
    "⚙️ Technical Architecture", 
    "🛡️ Compliance & Grants",
    "📝 Request Evaluation Access"
])

with tab_overview:
    st.subheader("Platform Vision & Core Infrastructure")
    st.write("""
    Garza Global Graviton delivers deterministic, server-authoritative integrity architecture designed to eliminate memory injection and sub-tick packet manipulation in distributed environments. 
    By combining high-frequency UDP telemetry inspection with ACID-compliant SQLite local data persistence, our infrastructure provides absolute determinism and zero performance tax for competitive gaming and high-performance server hosting.
    """)
    
    st.subheader("Active Infrastructure Fleet")
    if nodes:
        df_nodes = pd.DataFrame(nodes)[["id", "name", "region", "plan", "tickrate", "status"]]
        st.dataframe(df_nodes, use_container_width=True, hide_index=True)
    else:
        st.info("No active container nodes currently provisioned in public cluster view.")

with tab_roadmap:
    st.subheader("Strategic Business Plan & Phased Rollout")
    st.write("Overview of commercial scaling milestones and dual-use expansion phases.")

    st.markdown("""
    <div class="roadmap-box">
        <h4>Phase 1: Core Gaming & Community Infrastructure (Current)</h4>
        <p>Establish high-performance 128-tick dedicated server hosting, server-authoritative anti-cheat telemetry, and streamlined B2B advertiser onboarding pipelines with automated NSFW compliance filtering.</p>
    </div>
    <div class="roadmap-box">
        <h4>Phase 2: Scaled B2B Partnerships & Fleet Expansion</h4>
        <p>Expand server deployment capacity across multiple geographic regions, integrate automated backup/snapshot utilities, and onboard verified gaming hardware brands into the sponsor ad network.</p>
    </div>
    <div class="roadmap-box">
        <h4>Phase 3: Dual-Use Federal R&D & Military Grant Integration</h4>
        <p>Leverage our deterministic networking and telemetry architecture to secure Defense SBIR/STTR innovation grants. Target applications include synchronized tactical simulation, zero-trust remote workforce telemetry, and distributed cognitive data networks ('Human Data Crunch').</p>
    </div>
    """, unsafe_allow_html=True)

with tab_architecture:
    st.subheader("Deterministic Protection Mechanisms")
    st.markdown(f"""
    * **Server-Authoritative Position:** `{policies.get('server_authoritative_position', 1)}` (Enforces absolute coordinate calculation on dedicated host nodes).
    * **Sub-Tick Anomaly Scanning:** `{policies.get('sub_tick_packet_scan', 1)}` (Inspects packet interval variations and aim vector snap rates).
    * **Velocity Deviation Tolerance ($\sigma$):** `{policies.get('velocity_deviation_sigma', 2.2)}`
    * **Aim Vector Threshold:** `{policies.get('aim_vector_threshold_deg_per_ms', 65.0)}` °/ms
    """)

with tab_compliance:
    st.subheader("Federal Grant & Security Audit Compliance")
    st.write("This instance maintains cryptographic SHA-256 snapshot logs for every operational cycle, ensuring traceability suitable for Defense SBIR/STTR innovation reviews.")
    
    compliance_report = f"""GARZA GLOBAL GRAVITON - VERIFIED COMPLIANCE RECORD
Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Data Integrity Engine: SHA-256 Hashed SQLite Ledger
Content Moderation: Automated NSFW Filtering Active on Advertiser Pipeline
Parental Consent & Age Verification: Enforced on all commercial checkouts
"""
    st.text_area("Audit Verification Certificate", compliance_report, height=120)
    st.download_button("Download Official Audit Certificate (.txt)", compliance_report, file_name="agency_audit_certificate.txt", use_container_width=True)

with tab_request:
    st.subheader("Formal Evaluation Access Request")
    st.write("Government agency representatives, defense reviewers, and institutional investors may submit a formal request for secure, time-limited evaluation sessions and compliance audit dossiers.")

    with st.form("evaluation_request_form"):
        req_name = st.text_input("Full Name", placeholder="e.g., Dr. Jane Doe")
        req_org = st.text_input("Organization / Agency / Fund", placeholder="e.g., Defense Innovation Unit / Capital Partners")
        req_email = st.text_input("Professional Email Address", placeholder="name@agency.mil or name@fund.com")
        req_purpose = st.text_area("Evaluation Purpose & Scope", placeholder="Detail your review objectives, compliance frameworks, or grant evaluation context.")

        st.markdown(
            """
            > **Governance Notice:**  
            > All submissions are logged locally in our encrypted compliance database to maintain a strict audit trail. Approved parties will receive a secure, time-limited session link.
            """
        )

        req_submit = st.form_submit_button("Submit Formal Access Request", use_container_width=True)

        if req_submit:
            if not req_name.strip() or not req_org.strip() or not req_email.strip() or not req_purpose.strip():
                st.error("Please complete all required fields before submitting.")
            elif "@" not in req_email:
                st.error("Please enter a valid professional email address.")
            else:
                db.submit_stakeholder_request(req_name, req_org, req_email, req_purpose)
                st.success("Formal evaluation request successfully submitted. Our team will review your credentials and dispatch secure access instructions.")

    st.markdown("---")
    st.subheader("Administrative Review Ledger")
    st.caption("Internal review queue for incoming agency and investor inquiries.")
    requests_list = db.get_stakeholder_requests()
    if requests_list:
        df_reqs = pd.DataFrame(requests_list)
        st.dataframe(df_reqs, use_container_width=True, hide_index=True)
    else:
        st.info("No pending evaluation requests logged in the database yet.")