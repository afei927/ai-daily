import json
import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import collect


class TestLoadSeen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "seen.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_returns_empty(self):
        self.assertEqual(collect.load_seen(self.path),
                         {"github": [], "mcp": []})

    def test_corrupt_json_returns_empty(self):
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertEqual(collect.load_seen(self.path),
                         {"github": [], "mcp": []})

    def test_wrong_type_returns_empty(self):
        with open(self.path, "w") as f:
            json.dump(["unexpected"], f)
        self.assertEqual(collect.load_seen(self.path),
                         {"github": [], "mcp": []})

    def test_valid_roundtrip(self):
        collect.save_seen({"github": ["a/b", "a/b", "c/d"], "mcp": ["x"]},
                          self.path)
        got = collect.load_seen(self.path)
        self.assertEqual(got["github"], ["a/b", "c/d"])
        self.assertEqual(got["mcp"], ["x"])


if __name__ == "__main__":
    unittest.main()
