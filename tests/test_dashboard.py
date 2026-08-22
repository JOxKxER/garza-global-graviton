import pytest
from src.dashboard import ClusterDashboard

def test_cluster_dashboard_layout_render():
    dash = ClusterDashboard()
    dash.update_worker_status("test_node", "ACTIVE", 2.1, 1000, "abcdef1234567890")
    dash.record_merkle_consensus("1" * 64)
    layout = dash.generate_layout()
    assert layout is not None
