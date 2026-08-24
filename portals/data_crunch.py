"""
portals/data_crunch.py - Human Data Crunch Distributed Cognitive Portal
Allows operators to view, claim, and complete decentralized verification tasks.
Run with: python -m streamlit run portals/data_crunch.py --server.port 8504
"""

import streamlit as st
import pandas as pd
import db_manager as db

st.set_page_config(page_title="Human Data Crunch Network", page_icon="🌐", layout="wide")

st.markdown("# 🌐 Human Data Crunch: Distributed Cognitive Mesh")
st.write("Decentralized data verification, quality oversight, and asynchronous task coordination network.")

tasks = db.get_crunch_tasks()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Total Network Tasks", value=len(tasks))
with col2:
    st.metric(label="Active Operators", value="1 (Local Node)")
with col3:
    st.metric(label="Reward Token", value="$DMS-GRAV")

st.markdown("---")
st.subheader("📋 Active Verification Queue")

if tasks:
    df_tasks = pd.DataFrame(tasks)
    st.dataframe(df_tasks, use_container_width=True, hide_index=True)
else:
    st.info("No verification tasks currently in the queue.")

st.markdown("### ➕ Create New Verification Task")
with st.form("new_crunch_task"):
    task_desc = st.text_input("Task Description / Component ID", placeholder="Audit CAD Tolerance Data - Assembly #402")
    assigned = st.text_input("Assigned Worker / Entity", value="Danville_Metal_Stamping")
    submit_task = st.form_submit_button("Queue Task on Mesh", use_container_width=True)
    
    if submit_task:
        if task_desc:
            db.create_crunch_task(task_desc, assigned)
            st.success("Task successfully queued on the distributed cognitive network!")
            st.rerun()
        else:
            st.error("Please enter a task description.")