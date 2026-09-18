import os
import time
import sqlite3
import json
import logging
import shutil
import signal
import sys
from datetime import datetime, timezone

# Configure local logging
logging.basicConfig(
    filename='advanced_pipeline.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AdvancedAutonomousPipeline:
    def __init__(self, input_dir: str, output_dir: str, quarantine_dir: str, db_path: str, max_file_size_mb: int = 10):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.quarantine_dir = quarantine_dir
        self.db_path = db_path
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.running = True
        
        # Ensure directory structure exists
        for d in [self.input_dir, self.output_dir, self.quarantine_dir]:
            os.makedirs(d, exist_ok=True)
            
        self._init_db()
        
        # Register graceful shutdown handlers. SIGBREAK is Windows-only and
        # is what lets a parent orchestrator (run_system.py) request a clean
        # stop via CTRL_BREAK_EVENT -- plain terminate()/TerminateProcess on
        # Windows does not invoke SIGINT/SIGTERM handlers at all.
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._handle_exit)

    def _handle_exit(self, signum, frame):
        """Handles graceful shutdown signals."""
        logging.info("Shutdown signal received. Exiting processing loop safely...")
        print("\nGraceful shutdown initiated...")
        self.running = False

    def _init_db(self):
        """Initializes local SQLite state ledger."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_ledger (
                    file_name TEXT PRIMARY KEY,
                    file_hash TEXT,
                    status TEXT,
                    processed_timestamp TEXT,
                    output_path TEXT
                )
            ''')
            conn.commit()

    def _is_processed(self, cursor, file_name: str) -> bool:
        """Checks local ledger using an active cursor."""
        cursor.execute('SELECT status FROM file_ledger WHERE file_name = ?', (file_name,))
        row = cursor.fetchone()
        return row is not None and row[0] == 'SUCCESS'

    def _log_state(self, cursor, conn, file_name: str, status: str, output_path: str = None):
        """Updates the SQLite state ledger using an active connection."""
        cursor.execute('''
            INSERT OR REPLACE INTO file_ledger (file_name, status, processed_timestamp, output_path)
            VALUES (?, ?, ?, ?)
        ''', (file_name, status, datetime.now(timezone.utc).isoformat(), output_path))
        conn.commit()

    def run(self):
        """Main autonomous execution loop with graceful shutdown and optimized connection handling."""
        print(f"Advanced pipeline active. Monitoring ledger and directory: {self.input_dir}")
        while self.running:
            try:
                if not os.path.exists(self.input_dir):
                    time.sleep(5)
                    continue

                files = os.listdir(self.input_dir)
                if files:
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        for file_name in files:
                            if not self.running:
                                break
                                
                            file_path = os.path.join(self.input_dir, file_name)
                            
                            if os.path.isfile(file_path) and not file_name.startswith('.'):
                                # Validate file size to prevent memory exhaustion
                                if os.path.getsize(file_path) > self.max_file_size_bytes:
                                    logging.warning(f"File exceeds size limit: {file_name}. Quarantining.")
                                    self._log_state(cursor, conn, file_name, 'QUARANTINED')
                                    shutil.move(file_path, os.path.join(self.quarantine_dir, file_name))
                                    continue

                                if self._is_processed(cursor, file_name):
                                    continue
                                    
                                logging.info(f"Ingesting target payload: {file_name}")
                                
                                try:
                                    structured_asset = self._transform_and_synthesize(file_path)
                                    
                                    output_filename = f"asset_{int(time.time())}_{os.path.splitext(file_name)[0]}.json"
                                    output_path = os.path.join(self.output_dir, output_filename)
                                    
                                    with open(output_path, 'w', encoding='utf-8') as f:
                                        json.dump(structured_asset, f, indent=4)
                                        
                                    self._log_state(cursor, conn, file_name, 'SUCCESS', output_path)
                                    logging.info(f"Asset successfully syndicated locally: {output_filename}")
                                    
                                    os.remove(file_path)
                                    
                                except Exception as processing_error:
                                    logging.error(f"Transformation failure on {file_name}: {str(processing_error)}")
                                    self._log_state(cursor, conn, file_name, 'QUARANTINED')
                                    shutil.move(file_path, os.path.join(self.quarantine_dir, file_name))
                                    
                time.sleep(10)
                
            except Exception as e:
                logging.error(f"Critical loop exception: {str(e)}")
                time.sleep(15)

        print("Pipeline successfully stopped.")

    def _transform_and_synthesize(self, file_path: str) -> dict:
        """Parses raw text/data streams, applies logic, and outputs structured metadata schemas."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read()
            
        if not raw_content.strip():
            raise ValueError("Payload contains empty or invalid text stream.")

        lines = raw_content.splitlines()
        payload_metadata = {
            "schema_version": "2.1",
            "ingestion_utc": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "total_characters": len(raw_content),
                "total_lines": len(lines),
                "entropy_indicator": round(len(set(raw_content)) / max(len(raw_content), 1), 4)
            },
            "syndication_packet": {
                "target_node": "local_distribution_cache",
                "payload_vector": [ord(c) % 100 for c in raw_content[:32]]
            },
            "content": raw_content.strip()
        }
        return payload_metadata

if __name__ == "__main__":
    INPUT_WATCH_DIR = "./data_inbox"
    OUTPUT_ASSET_DIR = "./assets_out"
    QUARANTINE_DIR = "./quarantine"
    DB_LEDGER_PATH = "./pipeline_state.db"
    
    pipeline = AdvancedAutonomousPipeline(
        input_dir=INPUT_WATCH_DIR,
        output_dir=OUTPUT_ASSET_DIR,
        quarantine_dir=QUARANTINE_DIR,
        db_path=DB_LEDGER_PATH
    )
    pipeline.run()
