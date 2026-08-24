"""
analytics_module.py - Telemetry Analytics & Audit Aggregator
Aggregates security metrics and token ledgers for Garza Global Graviton.
"""

import db_manager as db

def generate_platform_metrics():
    nodes = db.get_all_nodes()
    events = db.get_recent_events(limit=1000)
    advertisers = db.get_all_advertisers()
    
    total_nodes = len(nodes)
    total_events = len(events)
    active_campaigns = len([ad for ad in advertisers if ad['status'] == 'Active'])
    
    # Categorize security vectors
    vectors = {}
    for ev in events:
        v = ev.get('vector', 'Unknown')
        vectors[v] = vectors.get(v, 0) + 1

    summary = {
        "total_nodes": total_nodes,
        "total_security_events": total_events,
        "active_advertiser_campaigns": active_campaigns,
        "vector_breakdown": vectors
    }
    return summary

if __name__ == "__main__":
    metrics = generate_platform_metrics()
    print("=== GARZA GLOBAL GRAVITON PLATFORM METRICS ===")
    for k, v in metrics.items():
        print(f"{k}: {v}")