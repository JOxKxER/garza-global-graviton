import time
from typing import Dict, Any, List
import numpy as np
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

console = Console()

class ClusterDashboard:
    def __init__(self, master_host: str = "127.0.0.1", master_port: int = 8765):
        self.master_host = master_host
        self.master_port = master_port
        self.start_time = time.time()
        self.total_processed_elements = 0
        self.total_bytes = 0
        self.verified_batches = 0
        self.latest_merkle_root = "Waiting for consensus..."
        self.worker_records: Dict[str, Dict[str, Any]] = {}
        self.latency_history: Dict[str, List[float]] = {}

    def update_worker_status(self, worker_id: str, status: str, latency_ms: float, elements: int, last_hash: str):
        if worker_id not in self.latency_history:
            self.latency_history[worker_id] = []
        if latency_ms > 0:
            self.latency_history[worker_id].append(latency_ms)
            if len(self.latency_history[worker_id]) > 20:
                self.latency_history[worker_id].pop(0)

        # Calculate jitter (std deviation of latency)
        lat_arr = self.latency_history[worker_id]
        jitter = float(np.std(lat_arr)) if len(lat_arr) > 1 else 0.0

        self.worker_records[worker_id] = {
            "status": status,
            "latency_ms": latency_ms,
            "jitter_ms": jitter,
            "elements": elements,
            "last_hash": last_hash[:16] + "...",
            "last_seen": time.time()
        }
        self.total_processed_elements += elements
        self.total_bytes += elements * 8  # 8 bytes per float64

    def record_merkle_consensus(self, root_hash: str):
        self.verified_batches += 1
        self.latest_merkle_root = root_hash

    def make_header(self) -> Panel:
        elapsed = max(time.time() - self.start_time, 1.0)
        uptime = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        mb_per_sec = (self.total_bytes / (1024 * 1024)) / elapsed

        header_text = Text()
        header_text.append("⚡ DISTRIBUTED COMPUTE CLUSTER - LIVE MONITOR\n", style="bold cyan")
        header_text.append(
            f"Coordinator: {self.master_host}:{self.master_port}  |  "
            f"Uptime: {uptime}  |  "
            f"Throughput: {mb_per_sec:.2f} MB/s  |  "
            f"Active Nodes: {len(self.worker_records)}",
            style="dim white"
        )
        return Panel(header_text, style="cyan")

    def make_worker_table(self) -> Table:
        table = Table(expand=True, box=None)
        table.add_column("Node ID", style="bold green")
        table.add_column("Status", justify="center")
        table.add_column("Latency", justify="right")
        table.add_column("Jitter", justify="right")
        table.add_column("Items", justify="right")
        table.add_column("Block Hash", style="magenta")

        if not self.worker_records:
            table.add_row("No workers", "[yellow]WAITING[/yellow]", "-", "-", "-", "-")
        else:
            for w_id, stats in self.worker_records.items():
                status_color = "green" if stats["status"] == "ACTIVE" else "yellow"
                table.add_row(
                    w_id,
                    f"[{status_color}]{stats['status']}[/{status_color}]",
                    f"{stats['latency_ms']:.1f}ms",
                    f"±{stats['jitter_ms']:.1f}ms",
                    f"{stats['elements']:,d}",
                    stats["last_hash"]
                )
        return table

    def make_integrity_panel(self) -> Panel:
        content = Text()
        content.append("🔒 MERKLE CONSENSUS & LEDGER\n", style="bold yellow")
        content.append(f"Verified Batches : {self.verified_batches}\n", style="white")
        content.append(f"Total Processed  : {self.total_processed_elements:,d} floats\n", style="white")
        content.append(f"Total Ingested   : {(self.total_bytes / (1024*1024)):.2f} MB\n", style="white")
        content.append(f"Latest MerkleRoot:\n{self.latest_merkle_root}\n", style="bold green" if len(self.latest_merkle_root) == 64 else "dim white")
        return Panel(content, title="Integrity Ledger", style="yellow")

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body")
        )
        layout["body"].split_row(
            Layout(name="workers", ratio=3),
            Layout(name="integrity", ratio=2)
        )

        layout["header"].update(self.make_header())
        layout["workers"].update(Panel(self.make_worker_table(), title="Connected Compute Nodes", style="green"))
        layout["integrity"].update(self.make_integrity_panel())
        return layout
