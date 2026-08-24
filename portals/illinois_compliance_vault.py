"""
portals/illinois_compliance_vault.py - Standalone Illinois LLC Compliance Vault
Run with: python -m streamlit run portals/illinois_compliance_vault.py --server.port 8503
"""

import streamlit as st
import pandas as pd
import db_manager as db

st.set_page_config(page_title="Corporate Compliance", page_icon="🏛️", layout="wide")

st.markdown("# 🏛️ Illinois LLC & Corporate Compliance Vault")
st.write("Independent module for tracking state filings, federal EIN documentation, and S-Corporation milestones.")

records = db.get_compliance_records()

if records:
    st.dataframe(pd.DataFrame(records)[["document_title", "filing_agency", "status", "due_date", "notes"]], use_container_width=True, hide_index=True)
else:
    st.info("No compliance records logged yet.")

with st.form("new_comp_form"):
    st.subheader("Log New Compliance Record")
    c_title = st.text_input("Document / Filing Title", placeholder="Illinois LLC Articles of Organization")
    c_agency = st.text_input("Filing Agency", placeholder="Illinois Secretary of State")
    c_status = st.selectbox("Status", ["Active / Filed", "Pending Submission", "Action Required"])
    c_date = st.text_input("Due Date / Filing Date", placeholder="2026-08-23")
    c_notes = st.text_area("Notes", placeholder="Confirmation numbers or details.")
    
    c_submit = st.form_submit_button("Save Compliance Record", use_container_width=True)
    if c_submit:
        if c_title and c_agency:
            db.add_compliance_record(c_title, c_agency, c_status, c_date, c_notes)
            st.success("Compliance record saved successfully!")
            st.rerun()
        else:
            st.error("Please provide a title and agency.")