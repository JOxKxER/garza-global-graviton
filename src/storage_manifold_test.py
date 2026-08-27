# src/storage_manifold_test.py
import unittest
from storage_manifold import compress_data  # Assuming this function exists in storage_manifold.py

class TestStorageManifold(unittest.TestCase):
    def test_compress_data(self):
        data = b'Some sample data'
        compressed_data = compress_data(data)
        self.assertIsNotNone(compressed_data)

if __name__ == '__main__':
    unittest.main()