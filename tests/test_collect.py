import json
import os
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import collect

MCP_HTML = """
<div class="grid">
<a href="/servers/auraspay-merchant-mcp" class="group"><div><div><h3 class="truncate font-semibold text-[15px]">AurasPay Merchant MCP</h3><svg><path d="M3 4"/></svg><span class="ml-auto shrink-0" title="09/20/2026, 06:47 PM">Added in 4 hours</span></div><p class="text-muted-foreground truncate text-xs">AurasPayOfficial</p></div></a>
<a href="/servers/gripforge" class="group"><div><h3 class="truncate font-semibold text-[15px]">GripForge</h3><span class="ml-auto shrink-0">Added in 1 day</span><p class="text-muted-foreground truncate text-xs">gripforgeai</p></div></a>
<a href="/servers/auraspay-merchant-mcp" class="group"><div><h3>duplicate</h3></div></a>
<a href="/servers?sort=latest" class="nav">Latest</a>
</div>
"""


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


class TestParseMcpso(unittest.TestCase):
    def test_extracts_fields_in_order(self):
        items = collect.parse_mcpso(MCP_HTML)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0], {
            "slug": "auraspay-merchant-mcp",
            "name": "AurasPay Merchant MCP",
            "author": "AurasPayOfficial",
            "added": "Added in 4 hours",
        })
        self.assertEqual(items[1]["slug"], "gripforge")
        self.assertEqual(items[1]["name"], "GripForge")

    def test_deduplicates_slugs(self):
        slugs = [i["slug"] for i in collect.parse_mcpso(MCP_HTML)]
        self.assertEqual(slugs, ["auraspay-merchant-mcp", "gripforge"])

    def test_ignores_non_slug_links(self):
        slugs = [i["slug"] for i in collect.parse_mcpso(MCP_HTML)]
        self.assertNotIn("servers?sort=latest", slugs)

    def test_empty_html(self):
        self.assertEqual(collect.parse_mcpso(""), [])

    def test_missing_name_falls_back_to_slug(self):
        items = collect.parse_mcpso('<a href="/servers/only-slug" class="x"></a>')
        self.assertEqual(items[0]["name"], "only-slug")
        self.assertEqual(items[0]["author"], "")
        self.assertEqual(items[0]["added"], "")


if __name__ == "__main__":
    unittest.main()
