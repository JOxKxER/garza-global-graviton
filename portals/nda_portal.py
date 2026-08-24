"""
portals/nda_portal.py - Standalone NDA Concept Preview Portal
Run with: python -m streamlit run portals/nda_portal.py --server.port 8504
"""

import streamlit as st
import db_manager as db

st.set_page_config(page_title="NDA Concept Preview", page_icon="🛡️", layout="wide")

if "nda_verified" not in st.session_state:
    st.session_state.nda_verified = False

if not st.session_state.nda_verified:
    st.markdown("# 🔒 Mandatory Non-Disclosure Agreement (NDA)")
    st.write("Reviewers must execute this agreement to access protected military, commercial, and scientific concepts.")

    with st.form("nda_form"):
        nda_name = st.text_input("Full Legal Name", placeholder="Johnathan Smith")
        nda_org = st.text_input("Representing Organization", placeholder="Defense Innovators Inc.")
        nda_email = st.text_input("Professional Email", placeholder="jsmith@organization.com")
        
        st.markdown("""
        > **CONFIDENTIALITY TERMS:**  
        > All simulations and conceptual designs viewed herein are the exclusive intellectual property of **Joel Garza / Garza Global Graviton**.
        """)
        nda_agree = st.checkbox("I agree to the confidentiality terms.")
        nda_submit = st.form_submit_button("Authenticate & Enter Portal", use_container_width=True)

        if nda_submit:
            if nda_name and nda_org and nda_email and nda_agree:
                db.log_nda_access(nda_name, nda_org, nda_email, "Modular Portal Access")
                st.session_state.nda_verified = True
                st.session_state.reviewer = f"{nda_name} ({nda_org})"
                st.rerun()
            else:
                st.error("Please complete all fields and check the agreement box.")
else:
    st.markdown(f'<div style="font-family: monospace; color: #facc15; background: rgba(250, 204, 21, 0.1); padding: 8px; border-radius: 4px; text-align: center; font-size: 12px; margin-bottom: 15px;">🛡️ SECURE NDA SESSION ACTIVE | REVIEWER: {st.session_state.reviewer} | IP OWNED BY JOEL GARZA / GARZA GLOBAL GRAVITON</div>', unsafe_allow_html=True)
    
    st.markdown("# 🛡️ Proprietary Technology Portfolio")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div style="background-color: #1e293b; border: 1px solid #38bdf8; padding: 20px; border-radius: 8px;">
            <h4>🎖️ Military Swarm Telemetry</h4>
            <p><b>Inventor:</b> Joel Garza</p>
            <p>Edge-deployed encrypted node synchronization for multi-domain tactical networks.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div style="background-color: #1e293b; border: 1px solid #38bdf8; padding: 20px; border-radius: 8px;">
            <h4>📈 Micro-Enterprise Compliance</h4>
            <p><b>Inventor:</b> Joel Garza</p>
            <p>Automated state/federal document generation and content moderation pipelines.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div style="background-color: #1e293b; border: 1px solid #38bdf8; padding: 20px; border-radius: 8px;">
            <h4>🔬 Distributed Cognitive Mesh</h4>
            <p><b>Inventor:</b> Joel Garza</p>
            <p>Asynchronous human-in-the-loop data verification network ('Human Data Crunch').</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Terminate Secure NDA Session"):
        st.session_state.nda_verified = False
        st.rerun()