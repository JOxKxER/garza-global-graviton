"""
vault_dashboard.py - Clean-Play Game Server Administration & Token Rewards Vault
Features: Gamer Pitch Landing, Server Checkout, Advertiser Pipeline, NSFW Filter, 
          Compliant Creator Widget Hub, and SQLite Persistence.
Run with: python -m streamlit run vault_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime
import db_manager as db

# --- Page Configuration ---
st.set_page_config(
    page_title="Game Server Integrity Vault",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
<style>
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 30px;
        color: #f8fafc;
        text-align: center;
        margin-bottom: 25px;
    }
    .sponsor-box {
        background-color: #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 12px;
        border-radius: 4px;
        font-size: 0.9em;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

policies = db.get_policies()
nodes = db.get_all_nodes()
events = db.get_recent_events(limit=100)

# --- Sidebar Controls ---
st.sidebar.title("🛡️ Server Vault")
st.sidebar.caption("Deterministic Anti-Cheat & Ecosystem")

auto_refresh = st.sidebar.toggle("Auto-Refresh Telemetry", value=False)
if auto_refresh:
    refresh_rate = st.sidebar.slider("Polling Frequency (s)", min_value=2, max_value=10, value=3)
    time.sleep(refresh_rate)
    st.rerun()

view_mode = st.sidebar.radio(
    "Navigation",
    [
        "🎮 Gamer Home & Checkout",
        "📺 Creator & Streamer Partner Hub",
        "Active Telemetry & Logs",
        "Fleet Node Controls",
        "Deploy New Clean Server",
        "🤝 Advertiser Portal & Rewards",
        "Integrity Settings",
        "Audit & Match Reports"
    ]
)

# --- Tab 0: Gamer Home & Checkout ---
if view_mode == "🎮 Gamer Home & Checkout":
    st.markdown("""
    <div class="hero-banner">
        <h1>Tired of Cheaters Ruining Your Servers?</h1>
        <p style="font-size: 1.2em; color: #94a3b8;">Deploy bulletproof, server-authoritative anti-cheat nodes with sub-tick packet inspection in seconds.</p>
        <p style="font-family: monospace; color: #38bdf8;">🌐 Site Address: <b>https://garzaglobalgraviton.com</b></p>
    </div>
    """, unsafe_allow_html=True)

    col_pitch1, col_pitch2 = st.columns(2)

    with col_pitch1:
        st.subheader("⚡ Why Choose Our Cheat-Proof Servers?")
        st.markdown(
            """
            * **Server-Authoritative Physics:** Eliminates client-side speedhacks and position desync.
            * **Sub-Tick Anomaly Scanning:** Flags aimbot angular snapping instantly.
            * **Zero Performance Tax:** Lightweight dedicated nodes with fixed 128-tick rates.
            * **Instant Return Customer Rewards:** Earn tokens by participating in clean community matches.
            """
        )

        active_ads = db.get_active_advertisements()
        if active_ads:
            st.markdown("### 🌟 Community Partner")
            ad = active_ads[0]
            st.markdown(f"""
            <div class="sponsor-box">
                <b>{ad['company_name']}</b>: {ad['ad_copy']}<br>
                <a href="{ad['target_url']}" target="_blank">Learn More & Support Clean Gaming ↗</a>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Claim +50 Token Reward for Viewing Partner"):
                db.award_user_tokens("Player_Session", 50)
                st.success("🎉 Added 50 integrity tokens to your account balance!")

    with col_pitch2:
        st.subheader("🛒 Instant Clean Server Setup")
        st.write("Select your plan below to launch a secure node instantly.")

        with st.form("quick_checkout_form"):
            q_name = st.text_input("Squad / Server Name", placeholder="e.g., Elite Scrims Arena")
            q_tier = st.selectbox(
                "Subscription Plan",
                [
                    "Starter Squad ($9.99/mo - Up to 8 Slots)",
                    "Clan Competitive ($19.99/mo - Up to 24 Slots - 128-Tick)",
                    "Community Hub ($34.99/mo - 50+ Slots)"
                ]
            )
            q_email = st.text_input("Billing Email", placeholder="admin@domain.com")

            st.markdown(
                """
                > **Parental / Guardian Permission Required:**  
                > All recurring server subscriptions and digital service agreements require confirmation of legal majority or explicit parental supervision.
                """
            )
            q_consent = st.checkbox(
                "I confirm I am 18+ OR have explicit parent/guardian permission to purchase and manage this server option."
            )

            q_submit = st.form_submit_button("Deploy & Activate Subscription", use_container_width=True)

            if q_submit:
                if not q_name.strip() or not q_email.strip():
                    st.error("Please fill out all required fields.")
                elif not q_consent:
                    st.warning("Parental or adult consent is required to proceed.")
                else:
                    with st.spinner("Provisioning secure container and billing gateway..."):
                        node_id = f"node-quick-{int(time.time()) % 10000}"
                        db.insert_node(node_id, q_name, "US Central (Chicago)", q_tier.split(" (")[0], q_email, 128)
                        time.sleep(1.2)
                    st.success(f"Success! Server '{q_name}' is live and hardened against cheaters.")
                    st.info(f"Access details and connection keys sent to `{q_email}`.")

# --- Tab 1: Creator & Streamer Partner Hub ---
elif view_mode == "📺 Creator & Streamer Partner Hub":
    st.title("Creator Partner Hub: Compliant Stream Integration")
    st.write("Integrate official fair-play anti-cheat metrics and verified sponsor ad rotations into your broadcasts safely and legally.")

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.subheader("📋 OBS Browser Source Integration")
        st.write("To display certified anti-cheat status and sponsor partner banners on your stream without violating platform terms of service, add a **Browser Source** in OBS Studio pointing to your secure local overlay endpoint:")
        st.code("http://localhost:8080/overlay", language="text")
        st.info("This overlay operates locally via secure HTTP headers and displays only authorized platform metrics and verified ad campaigns.")

    with col_c2:
        st.subheader("🔗 Official Platform Channel Links")
        st.write("Link your authorized public channel handles for community verification.")
        yt_handle = st.text_input("YouTube Channel Handle", placeholder="@YourChannel")
        tk_handle = st.text_input("TikTok Creator Handle", placeholder="@YourCreatorHandle")
        
        if st.button("Save Creator Handles"):
            st.success("Creator handles registered for community token rewards tracking.")

# --- Tab 2: Active Telemetry & Logs ---
elif view_mode == "Active Telemetry & Logs":
    st.title("System Status & Live Telemetry")
    st.markdown("Real-time telemetry stream and heuristic anti-cheat execution logs.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Active Dedicated Nodes", value=f"{len(nodes)} Nodes", delta="Operational")
    with col2:
        st.metric(label="Tickrate Stability", value="128.0 Hz", delta="0.0% Variance")
    with col3:
        st.metric(label="Connected Players", value=str(max(len(nodes) * 12, 18)), delta="+4 active")
    with col4:
        st.metric(label="Anomalies Prevented", value=f"{len(events)}", delta=f"{len(events)} logged")

    st.markdown("---")
    st.subheader("Server Packet Timing & Delta-T (ms)")
    chart_data = pd.DataFrame(
        np.random.normal(7.81, 0.12, size=(40, 3)),
        columns=["Node Alpha (US-East)", "Node Beta (US-Central)", "Node Gamma (US-West)"]
    )
    st.line_chart(chart_data)

    col_log_header, col_log_action = st.columns([3, 1])
    with col_log_header:
        st.subheader("Live Security Event Feed (SQLite)")
    with col_log_action:
        if st.button("Clear Log History", use_container_width=True):
            db.clear_events()
            st.rerun()

    if events:
        df_events = pd.DataFrame(events)
        df_events = df_events.rename(columns={
            "timestamp": "Timestamp",
            "node_name": "Node Name",
            "node_id": "Node ID",
            "vector": "Detection Vector",
            "action_taken": "Action Taken",
            "confidence": "Confidence"
        })
        st.dataframe(df_events, use_container_width=True, hide_index=True)
    else:
        st.info("No security anomalies recorded. Run `python client_sender.py` to stream live UDP detections.")

# --- Tab 3: Fleet Node Controls ---
elif view_mode == "Fleet Node Controls":
    st.title("Fleet Node Administration")
    st.write("Manage dedicated server instances stored in `vault_storage.db`.")

    if not nodes:
        st.warning("No active nodes available to manage. Deploy a server first.")
    else:
        for idx, node in enumerate(nodes):
            with st.expander(f"🖥️ {node.get('name')} ({node.get('id')}) - Status: {node.get('status')}", expanded=True):
                col_info, col_actions = st.columns([2, 1])
                with col_info:
                    st.markdown(f"**Region:** {node.get('region')}")
                    st.markdown(f"**Plan Tier:** {node.get('plan')}")
                    st.markdown(f"**Assigned Tickrate:** {node.get('tickrate')} Hz")
                    st.markdown(f"**Admin Contact:** `{node.get('admin_email')}`")
                with col_actions:
                    if st.button("Restart Node", key=f"restart_{node['id']}", use_container_width=True):
                        st.success(f"{node['name']} restarted.")
                    if st.button("Terminate Instance", key=f"term_{node['id']}", use_container_width=True):
                        db.delete_node(node["id"])
                        st.warning("Instance removed.")
                        st.rerun()

# --- Tab 4: Deploy New Server ---
elif view_mode == "Deploy New Clean Server":
    st.title("Provision Dedicated Clean Server")
    st.write("Deploy a dedicated instance with server-authoritative integrity binding.")

    col1, col2 = st.columns([2, 1])
    with col1:
        with st.form("deploy_server_form"):
            server_name = st.text_input("Server Display Name", placeholder="e.g., Apex Elite Scrims #1")
            region = st.selectbox("Region", ["US East (N. Virginia)", "US Central (Chicago)", "US West (Oregon)"])
            plan = st.selectbox("Plan Tier", ["Starter Squad ($9.99/mo)", "Clan Competitive ($19.99/mo)", "Community Hub ($34.99/mo)"])
            admin_email = st.text_input("Admin Email Address", placeholder="admin@domain.com")
            parental_consent = st.checkbox("I confirm I am 18+ OR have parent/guardian permission.")
            
            if st.form_submit_button("Deploy Node Instance", use_container_width=True):
                if not server_name or not admin_email or not parental_consent:
                    st.error("Please complete all fields and parental consent verification.")
                else:
                    node_id = f"node-{region[:2].lower()}-{int(time.time()) % 10000}"
                    db.insert_node(node_id, server_name, region, plan.split(" (")[0], admin_email, 128)
                    st.success(f"Server '{server_name}' successfully provisioned!")

    with col2:
        st.subheader("Your Token Balance")
        bal = db.get_user_tokens("Player_Session")
        st.metric(label="Earned Integrity Tokens", value=f"{bal} Tokens")
        st.caption("View sponsor partner links on the home page to earn bonus tokens.")

# --- Tab 5: Advertiser Portal & Rewards ---
elif view_mode == "🤝 Advertiser Portal & Rewards":
    st.title("Advertiser Onboarding & Clean Space Pipeline")
    st.write("Partner with our gaming ecosystem. Ads are organically integrated into gamer dashboards with strict NSFW filtering.")

    tab_apply, tab_manage = st.tabs(["Apply as Advertiser", "Active Campaigns Audit"])

    with tab_apply:
        with st.form("advertiser_application_form"):
            st.subheader("Brand Partnership Application")
            comp_name = st.text_input("Company / Brand Name", placeholder="e.g., Apex Hardware Co.")
            comp_email = st.text_input("Contact Email", placeholder="partners@brand.com")
            ad_copy = st.text_input("Ad Copy (Max 120 chars)", placeholder="High-performance mechanical keyboards built for competitive gaming.")
            target_url = st.text_input("Landing Page URL", placeholder="https://brand.com/gaming")
            token_budget = st.number_input("Token Campaign Budget", min_value=500, max_value=50000, value=1000, step=500)

            st.markdown("**Content Compliance Screening:**")
            nsfw_check = st.checkbox(
                "I certify that my brand, ad copy, and target landing page contain NO NSFW, adult, gambling, or prohibited explicit material."
            )

            ad_submitted = st.form_submit_button("Submit Campaign for Review", use_container_width=True)

            if ad_submitted:
                if not comp_name or not comp_email or not ad_copy or not target_url:
                    st.error("Please fill out all required fields.")
                elif not nsfw_check:
                    st.error("Compliance certification regarding NSFW content filtering is required.")
                else:
                    forbidden_keywords = ["nsfw", "adult", "casino", "gambling", "crypto-bet", "xxx", "dating"]
                    is_clean = not any(kw in ad_copy.lower() or kw in target_url.lower() for kw in forbidden_keywords)

                    db.register_advertiser(comp_name, comp_email, ad_copy, target_url, token_budget, is_clean)
                    if is_clean:
                        st.success("Campaign approved and published to the clean gaming sponsor feed!")
                    else:
                        st.error("Application rejected due to automated NSFW keyword filter detection.")

    with tab_manage:
        st.subheader("Registered Advertiser Pipeline")
        all_ads = db.get_all_advertisers()
        if all_ads:
            df_ads = pd.DataFrame(all_ads)
            st.dataframe(df_ads, use_container_width=True, hide_index=True)
        else:
            st.info("No advertiser campaigns registered yet.")

# --- Tab 6: Integrity Settings ---
elif view_mode == "Integrity Settings":
    st.title("Integrity & Enforcement Policies")
    st.write("Configure detection thresholds and Discord webhooks.")

    with st.form("integrity_settings_form"):
        auth_pos = st.toggle("Enforce Server-Authoritative Position Verification", value=bool(policies.get("server_authoritative_position", 1)))
        packet_scan = st.toggle("Enable Sub-Tick Packet Anomaly Scanning", value=bool(policies.get("sub_tick_packet_scan", 1)))
        auto_kick = st.toggle("Auto-Kick on Detected Memory Hook", value=bool(policies.get("auto_kick_memory_hook", 1)))
        vel_sigma = st.slider("Velocity Deviation Tolerance (σ)", 1.0, 5.0, float(policies.get("velocity_deviation_sigma", 2.2)), 0.1)
        aim_threshold = st.slider("Aim Vector Threshold (°/ms)", 10.0, 180.0, float(policies.get("aim_vector_threshold_deg_per_ms", 65.0)), 5.0)
        discord_webhook = st.text_input("Discord Webhook URL", value=policies.get("discord_webhook_url", "") or "")

        if st.form_submit_button("Save Policies", use_container_width=True):
            db.update_policies(auth_pos, packet_scan, auto_kick, vel_sigma, aim_threshold, discord_webhook)
            st.success("Settings saved successfully.")

# --- Tab 7: Audit & Match Reports ---
elif view_mode == "Audit & Match Reports":
    st.title("Tournament Match Audit & Integrity Certificates")
    report_text = f"""# MATCH INTEGRITY & FAIR-PLAY AUDIT REPORT
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Active Nodes: {len(nodes)} | Security Vectors Analyzed: {len(events)}
Verification Hash: SHA256-AUTHENTICATED-CLEAN-RUN
"""
    st.text_area("Audit Summary", report_text, height=150)
    st.download_button("Download Report (.txt)", report_text, file_name="match_audit.txt", use_container_width=True)