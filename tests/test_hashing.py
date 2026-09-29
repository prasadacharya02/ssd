import hashlib
from pathlib import Path
import tempfile
import unittest

from storage.hashing import sha256_file


class StreamingHashTests(unittest.TestCase):
    def test_streaming_hash_matches_hashlib(self):
        payload = bytes(range(256)) * 10000
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.bin"
            path.write_bytes(payload)

            expected = hashlib.sha256(payload).hexdigest()
            self.assertEqual(sha256_file(path, chunk_size=257), expected)

    def test_invalid_chunk_size_is_rejected(self):
        with self.assertRaises(ValueError):
            sha256_file("missing.bin", chunk_size=0)


if __name__ == "__main__":
    unittest.main()
