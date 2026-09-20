import json
import os
import tempfile
import unittest
from unittest import mock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import collect

MCP_HTML = """
<div class="grid">
<a href="/servers/auraspay-merchant-mcp" class="group"><div><div><h3 class="truncate font-semibold text-[15px]">AurasPay Merchant MCP</h3><svg><path d="M3 4"/></svg><span class="ml-auto shrink-0" title="09/20/2026, 06:47 PM">Added in 4 hours</span></div><p class="text-muted-foreground truncate text-xs">AurasPayOfficial</p><p class="text-muted-foreground line-clamp-2 min-h-10 text-sm">Long description here</p></div></a>
<a href="/servers/gripforge" class="group"><div><h3 class="truncate font-semibold text-[15px]">GripForge</h3><span class="ml-auto shrink-0">Added in 1 day</span><p class="text-muted-foreground truncate text-xs">gripforgeai</p></div></a>
<a href="/servers/nilyo" class="group"><div><h3 class="truncate font-semibold text-[15px]">Nilyo</h3><span class="ml-auto shrink-0">Added 2 days ago</span><p class="text-muted-foreground line-clamp-2 min-h-10 text-sm">Your own LinkedIn and more, usable from any agent</p></div></a>
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
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0], {
            "slug": "auraspay-merchant-mcp",
            "name": "AurasPay Merchant MCP",
            "author": "AurasPayOfficial",
            "added": "Added in 4 hours",
        })
        self.assertEqual(items[1]["slug"], "gripforge")
        self.assertEqual(items[1]["name"], "GripForge")

    def test_card_without_author_does_not_take_description(self):
        items = collect.parse_mcpso(MCP_HTML)
        self.assertEqual(items[2]["slug"], "nilyo")
        self.assertEqual(items[2]["name"], "Nilyo")
        self.assertEqual(items[2]["author"], "")

    def test_deduplicates_slugs(self):
        slugs = [i["slug"] for i in collect.parse_mcpso(MCP_HTML)]
        self.assertEqual(slugs, ["auraspay-merchant-mcp", "gripforge", "nilyo"])

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


class TestSelectNew(unittest.TestCase):
    def test_filters_seen_and_preserves_order(self):
        got = collect.select_new(["a", "b", "c"], {"b"}, limit=10)
        self.assertEqual(got, ["a", "c"])

    def test_caps_at_limit(self):
        got = collect.select_new(["a", "b", "c"], set(), limit=2)
        self.assertEqual(got, ["a", "b"])


class TestOrderByCreated(unittest.TestCase):
    def test_newest_first(self):
        repos = [{"full_name": "old", "created_at": "2026-09-01T00:00:00Z"},
                 {"full_name": "new", "created_at": "2026-09-19T00:00:00Z"},
                 {"full_name": "mid", "created_at": "2026-09-10T00:00:00Z"}]
        self.assertEqual([r["full_name"] for r in collect.order_by_created(repos)],
                         ["new", "mid", "old"])

    def test_missing_created_at_sorts_last(self):
        repos = [{"full_name": "a"}, {"full_name": "b", "created_at": "2026-01-01T00:00:00Z"}]
        self.assertEqual([r["full_name"] for r in collect.order_by_created(repos)],
                         ["b", "a"])


class TestRenderLines(unittest.TestCase):
    def test_repo_line(self):
        repo = {"full_name": "o/r", "html_url": "https://github.com/o/r",
                "stargazers_count": 42, "description": "hello"}
        self.assertEqual(collect.render_repo_line(repo),
                         "- [o/r](https://github.com/o/r) ⭐ 42 — hello")

    def test_repo_line_without_description(self):
        repo = {"full_name": "o/r", "html_url": "https://github.com/o/r",
                "stargazers_count": 1, "description": None}
        self.assertIn("No description", collect.render_repo_line(repo))

    def test_repo_line_truncates_description(self):
        repo = {"full_name": "o/r", "html_url": "u", "stargazers_count": 1,
                "description": "x" * 200}
        self.assertLessEqual(len(collect.render_repo_line(repo).split("— ")[1]), 80)

    def test_mcp_line(self):
        item = {"slug": "s", "name": "Name", "author": "Auth", "added": "Added in 1 hour"}
        self.assertEqual(collect.render_mcp_line(item),
                         "- [Name](https://mcp.so/servers/s) — Auth (Added in 1 hour)")

    def test_mcp_line_minimal(self):
        item = {"slug": "only", "name": "", "author": "", "added": ""}
        self.assertEqual(collect.render_mcp_line(item),
                         "- [only](https://mcp.so/servers/only)")


class TestRenderDocument(unittest.TestCase):
    def test_sections_and_headers(self):
        doc = collect.render_document("2026-09-20", [
            ("常青榜 · AI Agent (GitHub)", "src-a", ["- line-a"]),
            ("今日新发现 · MCP Server", "src-b", []),
        ])
        self.assertTrue(doc.startswith("# AI Daily — 2026-09-20\n"))
        self.assertIn("## 常青榜 · AI Agent (GitHub)\nSource: src-a\n", doc)
        self.assertIn("- line-a", doc)
        self.assertIn("- (今日无新增)", doc)

    def test_ends_with_single_newline(self):
        doc = collect.render_document("2026-09-20", [("t", "s", ["- x"])])
        self.assertTrue(doc.endswith("\n"))
        self.assertFalse(doc.endswith("\n\n"))


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.old)
        self.tmp.cleanup()

    def test_writes_file_and_updates_ledger(self):
        repos = [
            {"full_name": "new/one", "html_url": "u1", "stargazers_count": 5,
             "description": "d1", "created_at": "2026-09-19T00:00:00Z"},
            {"full_name": "new/two", "html_url": "u2", "stargazers_count": 3,
             "description": "d2", "created_at": "2026-09-18T00:00:00Z"},
        ]
        evergreen = [
            {"full_name": "star/top", "html_url": "u3", "stargazers_count": 999,
             "description": "top", "created_at": "2015-01-01T00:00:00Z"},
        ]
        mcp_items = [
            {"slug": "s1", "name": "S1", "author": "A", "added": "Added in 1 hour"},
        ]

        def fake_search(query, token, per_page=100):
            if "stars:>500" in query or "stars:>100" in query:
                return {"items": evergreen}
            return {"items": repos}

        with mock.patch.object(collect, "github_search", fake_search), \
             mock.patch.object(collect, "fetch_mcpso", lambda url=None: "html"), \
             mock.patch.object(collect, "parse_mcpso", lambda h: mcp_items):
            rc = collect.main()

        self.assertEqual(rc, 0)
        files = os.listdir("daily")
        self.assertEqual(len(files), 1)
        doc = open(os.path.join("daily", files[0]), encoding="utf-8").read()
        self.assertIn("new/one", doc)
        self.assertIn("star/top", doc)
        self.assertIn("S1", doc)

        seen = collect.load_seen()
        self.assertIn("new/one", seen["github"])
        self.assertIn("new/two", seen["github"])
        self.assertIn("star/top", seen["github"])
        self.assertIn("s1", seen["mcp"])

    def test_second_run_has_no_new_items(self):
        repos = [{"full_name": "new/one", "html_url": "u1", "stargazers_count": 5,
                  "description": "d1", "created_at": "2026-09-19T00:00:00Z"}]

        def fake_search(query, token, per_page=100):
            if "stars:>" in query:
                return {"items": []}
            return {"items": repos}

        with mock.patch.object(collect, "github_search", fake_search), \
             mock.patch.object(collect, "fetch_mcpso", lambda url=None: "html"), \
             mock.patch.object(collect, "parse_mcpso", lambda h: []):
            collect.main()
            collect.main()

        files = sorted(os.listdir("daily"))
        doc = open(os.path.join("daily", files[-1]), encoding="utf-8").read()
        self.assertIn("- (今日无新增)", doc)


if __name__ == "__main__":
    unittest.main()
