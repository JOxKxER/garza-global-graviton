"""Integration checks for the loopback-only Joker service."""

import importlib
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class JokerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        os.environ["JOKER_DB_KEY"] = "db-key-for-test-only-0123456789-abcdef"
        os.environ["JOKER_MESH_TOKEN"] = "mesh-token-for-test-only-0123456789"
        os.environ["JOKER_DB_PATH"] = str(Path(self.temporary_directory.name) / "joker.db")
        import joker_local_copilot

        self.service = importlib.reload(joker_local_copilot)
        self.client = TestClient(self.service.app)
        self.client.__enter__()
        self.headers = {"Authorization": f"Bearer {os.environ['JOKER_MESH_TOKEN']}"}

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temporary_directory.cleanup()

    def test_goal_requires_token_and_creates_sequenced_steps(self) -> None:
        rejected = self.client.post("/goal", json={"prompt": "Prepare a release"})
        self.assertEqual(rejected.status_code, 401)

        response = self.client.post(
            "/goal",
            headers=self.headers,
            json={"prompt": "Prepare a release", "context": "Work in a 10-minute interval"},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(len(body["steps"]), 5)
        self.assertEqual(body["steps"][0]["status"], "READY")
        self.assertEqual(body["steps"][1]["status"], "QUEUED")

    def test_command_is_allowlisted_and_audited(self) -> None:
        response = self.client.post(
            "/command", headers=self.headers, json={"command": "python_version"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "SUCCEEDED")

        with self.service.db_connection() as connection:
            logged_command = connection.execute("SELECT status FROM command_logs").fetchone()
        self.assertEqual(logged_command["status"], "SUCCEEDED")

    def test_database_cannot_be_read_by_plain_sqlite(self) -> None:
        with self.assertRaises(sqlite3.DatabaseError):
            plain_connection = sqlite3.connect(os.environ["JOKER_DB_PATH"])
            try:
                plain_connection.execute("SELECT * FROM goals").fetchall()
            finally:
                plain_connection.close()


if __name__ == "__main__":
    unittest.main()