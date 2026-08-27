import math

class ToroidalMeshRouter:
    def __init__(self, grid_size=(10, 10)):
        self.width, self.height = grid_size

    def calculate_toroidal_distance(self, node_a, node_b):
        """Calculates the shortest distance between two nodes on a toroidal wrap-around surface."""
        ax, ay = node_a
        bx, by = node_b
        
        dx = abs(ax - bx)
        dy = abs(ay - by)
        
        # Account for toroidal wrap-around boundaries
        dx = min(dx, self.width - dx)
        dy = min(dy, self.height - dy)
        
        return math.sqrt(dx**2 + dy**2)

    def route_packet(self, source_node, target_node, payload_size_kb):
        """Simulates optimal low-latency packet routing across the toroidal node network."""
        distance = self.calculate_toroidal_distance(source_node, target_node)
        simulated_latency_ms = round(distance * 1.42, 2)
        
        return {
            "status": "success",
            "topology": f"{self.width}x{self.height} Toroidal Grid",
            "source": source_node,
            "target": target_node,
            "hop_distance": round(distance, 2),
            "estimated_latency_ms": simulated_latency_ms,
            "routing_status": "Optimized & Low-Latency"
        }