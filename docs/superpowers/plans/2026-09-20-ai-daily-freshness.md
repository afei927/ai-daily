# AI Daily 内容新鲜度改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让每日产物 `daily/YYYY-MM-DD.md` 每天包含真正新增的仓库/MCP server，同时保留一个稳定的 top 10 常青榜。

**Architecture:** 用一个纯 Python 模块 `scripts/collect.py` 承担抓取、解析、台账去重、Markdown 渲染；`scripts/fetch.sh` 退化为调用它的薄包装（保持 workflow 不变）。新增 `state/seen.json` 作为累计去重台账，由 workflow 现有的 `git add .` 一并提交。

**Tech Stack:** Python 3 标准库（`urllib.request` / `json` / `re` / `html` / `unittest`），bash，GitHub Actions。**零第三方依赖。**

## Global Constraints

- 不引入任何第三方 Python 依赖；只用标准库（Actions 里不执行 `pip install`）。
- 不改动 `.github/workflows/ai-daily.yml`（入口仍是 `bash scripts/fetch.sh`）。
- 常青榜固定为 **top 10**（AI Agent 与 MCP Server 各 10 条）。
- 新发现区每区最多 **10** 条。
- GitHub 新发现候选窗口为 **created:>7 天**。
- 台账路径 `state/seen.json`，结构 `{"github": [...], "mcp": [...]}`。
- 产物路径 `daily/YYYY-MM-DD.md`（保留现有命名）。
- 条目格式沿用现有风格：`- [owner/repo](url) ⭐ N — 描述`。
- 网络失败不得中断整个脚本；失败区块写 `- (抓取失败)`，空区块写 `- (今日无新增)`。
- 脚本整体退出码恒为 0（python 解释器缺失除外），保证 workflow 的 commit 步骤能提交已有内容。
- 所有面向用户的文案为中文（区块标题），与现有产物一致。

---

### Task 1: 模块骨架与累计台账

**Files:**
- Create: `scripts/collect.py`
- Create: `tests/test_collect.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: 无（首个任务）
- Produces:
  - `SEEN_PATH: str` = `"state/seen.json"`
  - `load_seen(path: str = SEEN_PATH) -> dict` — 返回 `{"github": list[str], "mcp": list[str]}`；文件缺失/损坏/类型错误时返回空台账
  - `save_seen(seen: dict, path: str = SEEN_PATH) -> None` — 去重排序后写盘

- [ ] **Step 1: 写失败测试**

创建 `tests/__init__.py`（空文件），然后创建 `tests/test_collect.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest tests.test_collect -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'collect'`

- [ ] **Step 3: 写最小实现**

创建 `scripts/collect.py`：

```python
#!/usr/bin/env python3
"""AI Daily collector: 抓取 AI Agent / MCP 头部与新增项目，渲染每日 Markdown。"""

import html
import json
import os
import re
import sys
import urllib.request
from datetime import date, timedelta

GITHUB_API = "https://api.github.com/search/repositories"
MCPSO_LATEST = "https://mcp.so/servers?sort=latest"
SEEN_PATH = os.path.join("state", "seen.json")
OUTDIR = "daily"
EVERGREEN_LIMIT = 10
NEW_LIMIT = 10
NEW_WINDOW_DAYS = 7

NO_NEW = ["- (今日无新增)"]
FETCH_FAIL = ["- (抓取失败)"]


def load_seen(path=SEEN_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {"github": [], "mcp": []}
    if not isinstance(data, dict):
        return {"github": [], "mcp": []}
    return {
        "github": [x for x in data.get("github", []) if isinstance(x, str)],
        "mcp": [x for x in data.get("mcp", []) if isinstance(x, str)],
    }


def save_seen(seen, path=SEEN_PATH):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    payload = {
        "github": sorted(set(seen.get("github", []))),
        "mcp": sorted(set(seen.get("mcp", []))),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m unittest tests.test_collect -v`
Expected: PASS（4 个测试）

- [ ] **Step 5: 提交**

```bash
git add scripts/collect.py tests/__init__.py tests/test_collect.py
git commit -m "feat: add collect module skeleton and seen ledger"
```

---

### Task 2: mcp.so 解析器

**Files:**
- Modify: `scripts/collect.py`
- Modify: `tests/test_collect.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `parse_mcpso(html_text: str) -> list[dict]` — 每项 `{"slug": str, "name": str, "author": str, "added": str}`，按出现顺序，slug 去重

- [ ] **Step 1: 写失败测试**

在 `tests/test_collect.py` 顶部（`import collect` 之后）加入常量，并在文件末尾 `if __name__` 之前加入测试类：

```python
MCP_HTML = """
<div class="grid">
<a href="/servers/auraspay-merchant-mcp" class="group"><div><div><h3 class="truncate font-semibold text-[15px]">AurasPay Merchant MCP</h3><svg><path d="M3 4"/></svg><span class="ml-auto shrink-0">Added in 4 hours</span></div><p class="text-muted-foreground truncate text-xs">AurasPayOfficial</p></div></a>
<a href="/servers/gripforge" class="group"><div><h3 class="truncate font-semibold text-[15px]">GripForge</h3><span class="ml-auto shrink-0">Added in 1 day</span><p class="text-muted-foreground truncate text-xs">gripforgeai</p></div></a>
<a href="/servers/auraspay-merchant-mcp" class="group"><div><h3>duplicate</h3></div></a>
<a href="/servers?sort=latest" class="nav">Latest</a>
</div>
"""


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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest tests.test_collect -v`
Expected: FAIL — `AttributeError: module 'collect' has no attribute 'parse_mcpso'`

- [ ] **Step 3: 写最小实现**

在 `scripts/collect.py` 的 `save_seen` 之后加入：

```python
_CARD_SPLIT = re.compile(r'<a href="/servers/([^"/]+)"')
_H3 = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)
_AUTHOR = re.compile(
    r'<p\s[^>]*class="[^"]*text-muted-foreground[^"]*"[^>]*>(.*?)</p>', re.S)
_ADDED = re.compile(r'<span class="ml-auto shrink-0">(.*?)</span>', re.S)
_TAGS = re.compile(r"<[^>]+>")


def _clean(fragment):
    return html.unescape(_TAGS.sub("", fragment)).strip()


def parse_mcpso(html_text):
    parts = _CARD_SPLIT.split(html_text)
    items = []
    seen_slugs = set()
    for i in range(1, len(parts) - 1, 2):
        slug = parts[i]
        segment = parts[i + 1]
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        name_m = _H3.search(segment)
        author_m = _AUTHOR.search(segment)
        added_m = _ADDED.search(segment)
        items.append({
            "slug": slug,
            "name": _clean(name_m.group(1)) if name_m else slug,
            "author": _clean(author_m.group(1)) if author_m else "",
            "added": _clean(added_m.group(1)) if added_m else "",
        })
    return items
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m unittest tests.test_collect -v`
Expected: PASS（9 个测试）

- [ ] **Step 5: 提交**

```bash
git add scripts/collect.py tests/test_collect.py
git commit -m "feat: parse mcp.so latest-servers cards"
```

---

### Task 3: 候选筛选与渲染函数

**Files:**
- Modify: `scripts/collect.py`
- Modify: `tests/test_collect.py`

**Interfaces:**
- Consumes: 无
- Produces:
  - `select_new(candidates: list[str], seen: set, limit: int = NEW_LIMIT) -> list[str]` — 保持顺序、剔除 `seen` 中已有的、截断到 `limit`
  - `order_by_created(repos: list[dict]) -> list[dict]` — 按 `created_at` 倒序（缺失视为空串）
  - `render_repo_line(repo: dict) -> str`
  - `render_mcp_line(item: dict) -> str`
  - `render_document(today: str, sections: list[tuple[str, str, list[str]]]) -> str`

- [ ] **Step 1: 写失败测试**

在 `tests/test_collect.py` 末尾（`if __name__` 之前）加入：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest tests.test_collect -v`
Expected: FAIL — `AttributeError: module 'collect' has no attribute 'select_new'`

- [ ] **Step 3: 写最小实现**

在 `scripts/collect.py` 的 `parse_mcpso` 之后加入：

```python
def select_new(candidates, seen, limit=NEW_LIMIT):
    out = []
    for key in candidates:
        if key in seen:
            continue
        out.append(key)
        if len(out) >= limit:
            break
    return out


def order_by_created(repos):
    return sorted(repos, key=lambda r: r.get("created_at") or "", reverse=True)


def render_repo_line(repo):
    desc = (repo.get("description") or "No description").replace("\n", " ").strip()[:80]
    return (f"- [{repo['full_name']}]({repo['html_url']}) "
            f"⭐ {repo['stargazers_count']} — {desc}")


def render_mcp_line(item):
    label = item.get("name") or item.get("slug", "")
    line = f"- [{label}](https://mcp.so/servers/{item.get('slug', '')})"
    if item.get("author"):
        line += f" — {item['author']}"
    if item.get("added"):
        line += f" ({item['added']})"
    return line


def render_document(today, sections):
    lines = [f"# AI Daily — {today}", ""]
    for title, source, body in sections:
        lines.append(f"## {title}")
        lines.append(f"Source: {source}")
        lines.append("")
        lines.extend(body if body else NO_NEW)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m unittest tests.test_collect -v`
Expected: PASS（22 个测试）

- [ ] **Step 5: 提交**

```bash
git add scripts/collect.py tests/test_collect.py
git commit -m "feat: add selection and markdown rendering helpers"
```

---

### Task 4: 网络抓取、主流程与 fetch.sh 接入

**Files:**
- Modify: `scripts/collect.py`
- Modify: `scripts/fetch.sh`

**Interfaces:**
- Consumes: `load_seen` / `save_seen` / `parse_mcpso` / `select_new` / `order_by_created` / `render_repo_line` / `render_mcp_line` / `render_document`
- Produces:
  - `github_search(query: str, token: str | None, per_page: int = 100) -> dict`
  - `fetch_mcpso(url: str = MCPSO_LATEST) -> str`
  - `main() -> int`

- [ ] **Step 1: 写失败测试**

在 `tests/test_collect.py` 末尾（`if __name__` 之前）加入。该测试用 `unittest.mock` 打桩网络函数，验证端到端编排、台账写入与文件落盘：

```python
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

        with unittest.mock.patch.object(collect, "github_search", fake_search), \
             unittest.mock.patch.object(collect, "fetch_mcpso", lambda url=None: "html"), \
             unittest.mock.patch.object(collect, "parse_mcpso", lambda h: mcp_items):
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

        with unittest.mock.patch.object(collect, "github_search", fake_search), \
             unittest.mock.patch.object(collect, "fetch_mcpso", lambda url=None: "html"), \
             unittest.mock.patch.object(collect, "parse_mcpso", lambda h: []):
            collect.main()
            collect.main()

        files = sorted(os.listdir("daily"))
        doc = open(os.path.join("daily", files[-1]), encoding="utf-8").read()
        self.assertIn("- (今日无新增)", doc)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python3 -m unittest tests.test_collect -v`
Expected: FAIL — `AttributeError: module 'collect' has no attribute 'main'`

- [ ] **Step 3: 写实现**

在 `scripts/collect.py` 的 `render_document` 之后加入（`import unittest.mock` 只出现在测试里，不进模块）：

```python
def github_search(query, token=None, per_page=100):
    from urllib.parse import urlencode
    params = urlencode({"q": query, "sort": "stars", "order": "desc",
                        "per_page": per_page})
    req = urllib.request.Request(f"{GITHUB_API}?{params}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ai-daily")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def fetch_mcpso(url=MCPSO_LATEST):
    req = urllib.request.Request(url)
    req.add_header("User-Agent",
                   "Mozilla/5.0 (compatible; ai-daily/1.0)")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _safe(fn):
    """Return (value, failed)."""
    try:
        return fn(), False
    except Exception as exc:  # noqa: BLE001 - 单源失败不应中断整体
        print(f"fetch failed: {exc}", file=sys.stderr)
        return None, True


def _body(items, failed, render):
    if failed:
        return FETCH_FAIL
    return [render(i) for i in items] if items else NO_NEW


def main():
    today = date.today().isoformat()
    token = os.environ.get("GITHUB_TOKEN") or None
    seen = load_seen()
    seen_gh = set(seen["github"])
    seen_mcp = set(seen["mcp"])

    ev_agent, f_ev_agent = _safe(lambda: github_search(
        "topic:ai-agent stars:>500", token, EVERGREEN_LIMIT).get("items", [])[:EVERGREEN_LIMIT])
    ev_mcp, f_ev_mcp = _safe(lambda: github_search(
        "topic:mcp-server stars:>100", token, EVERGREEN_LIMIT).get("items", [])[:EVERGREEN_LIMIT])

    since = (date.today() - timedelta(days=NEW_WINDOW_DAYS)).isoformat()

    def fetch_new_github():
        a = github_search(f"topic:ai-agent created:>{since}", token, 100).get("items", [])
        b = github_search(f"topic:mcp-server created:>{since}", token, 100).get("items", [])
        return a + b

    raw_gh, f_new_gh = _safe(fetch_new_github)
    if not f_new_gh:
        ordered = order_by_created(raw_gh)
        by_key = {r["full_name"]: r for r in ordered}
        picked = select_new([r["full_name"] for r in ordered], seen_gh, NEW_LIMIT)
        new_gh = [by_key[k] for k in picked]
        seen_gh.update(picked)
    else:
        new_gh = []

    raw_mcp, f_new_mcp = _safe(lambda: parse_mcpso(fetch_mcpso(MCPSO_LATEST)))
    if not f_new_mcp:
        by_slug = {m["slug"]: m for m in raw_mcp}
        picked = select_new([m["slug"] for m in raw_mcp], seen_mcp, NEW_LIMIT)
        new_mcp = [by_slug[s] for s in picked]
        seen_mcp.update(picked)
    else:
        new_mcp = []

    seen_gh.update(r["full_name"] for r in (ev_agent or []) + (ev_mcp or []))
    save_seen({"github": sorted(seen_gh), "mcp": sorted(seen_mcp)})

    doc = render_document(today, [
        ("常青榜 · AI Agent (GitHub)",
         "GitHub Search (topic:ai-agent, sort by stars)",
         _body(ev_agent, f_ev_agent, render_repo_line)),
        ("常青榜 · MCP Server (GitHub)",
         "GitHub Search (topic:mcp-server, sort by stars)",
         _body(ev_mcp, f_ev_mcp, render_repo_line)),
        ("今日新发现 · GitHub",
         f"GitHub Search (created:>{since}, topic:ai-agent / topic:mcp-server)",
         _body(new_gh, f_new_gh, render_repo_line)),
        ("今日新发现 · MCP Server",
         MCPSO_LATEST,
         _body(new_mcp, f_new_mcp, render_mcp_line)),
    ])

    os.makedirs(OUTDIR, exist_ok=True)
    outfile = os.path.join(OUTDIR, f"{today}.md")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Written: {outfile}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python3 -m unittest tests.test_collect -v`
Expected: PASS（24 个测试）

- [ ] **Step 5: 把 fetch.sh 改为薄包装**

用以下内容整体替换 `scripts/fetch.sh`（保留可执行位）：

```bash
#!/usr/bin/env bash
# AI Daily 入口：委托给 scripts/collect.py
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/collect.py
```

- [ ] **Step 6: 端到端本地验证（真实网络）**

Run: `bash scripts/fetch.sh && cat "daily/$(date +%Y-%m-%d).md"`

Expected:
- 打印 `Written: daily/2026-09-20.md`（日期以当天为准）。
- 文件含 4 个区块；两个常青榜各 10 条；两个"今日新发现"区有内容（或 `- (今日无新增)`）。
- 不存在空的区块（区块标题下必须至少有一行 `- `）。

- [ ] **Step 7: 连跑第二次，验证去重**

Run: `bash scripts/fetch.sh && cat "daily/$(date +%Y-%m-%d).md"`

Expected: "今日新发现 · GitHub" 与 "今日新发现 · MCP Server" 两个区块此时应为 `- (今日无新增)`，或与第一次的条目完全不重叠。常青榜保持一致。

- [ ] **Step 8: 验证台账损坏回退**

Run: `echo 'not json' > state/seen.json && bash scripts/fetch.sh && head -c 200 state/seen.json`

Expected: 脚本不崩溃；运行后 `state/seen.json` 是合法 JSON（重新产出了新发现条目）。

- [ ] **Step 9: 验证 workflow 会提交新文件**

Run: `git status --porcelain`

Expected: 输出包含 `daily/<date>.md` 与 `state/seen.json`（两者都在待提交列表内，workflow 的 `git add .` 会覆盖它们）。

- [ ] **Step 10: 提交**

```bash
git add scripts/collect.py scripts/fetch.sh state/seen.json daily/
git commit -m "feat: daily freshness via seen-ledger and created-window sources"
```

---

### Task 5: 更新 README 说明

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: 无
- Produces: 无（文档）

- [ ] **Step 1: 更新数据源表与说明**

把 `README.md` 的"数据源"表替换为下面内容，并在表格后补一段"去重机制"说明：

```markdown
## 数据源

| 来源 | 内容 |
|------|------|
| [GitHub Topics](https://github.com/topics/ai-agent) | AI Agent 常青榜（按 star 取 top 10） |
| [GitHub Topics](https://github.com/topics/mcp-server) | MCP Server 常青榜（按 star 取 top 10） |
| [GitHub Search](https://github.com/search) | 近 7 天新建的 AI Agent / MCP 项目（今日新发现） |
| [MCP.so](https://mcp.so/servers?sort=latest) | 最新上架 MCP Server（今日新发现） |

## 去重机制

`state/seen.json` 记录所有已发布过的条目（累计、永久）。"今日新发现"区只输出
从未发布过的条目，因此不会重复；"常青榜"按设计每天重复，用于随时查阅当前头部项目。
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: document freshness sources and dedup ledger"
```

---

## Self-Review

**1. Spec coverage**

| Spec 要求 | 对应任务 |
|-----------|----------|
| 台账 `state/seen.json`，缺失/损坏回退 | Task 1 |
| mcp.so 最新 server 解析（h3/作者/时间） | Task 2 |
| 新发现去重 + 上限 10 | Task 3（`select_new`）、Task 4（编排） |
| GitHub 近 7 天候选 + 按 created_at 倒序 | Task 3（`order_by_created`）、Task 4 |
| 常青榜 top 10（两区） | Task 4 |
| 每日文件 4 区块 | Task 3（`render_document`）、Task 4 |
| 空区块 `(今日无新增)` / 失败 `(抓取失败)` | Task 3（`NO_NEW`）、Task 4（`_body`） |
| 删除失效的 Skills 区块 | Task 4（重写 fetch.sh，不再包含） |
| GitHub 带 token、缺失则匿名 | Task 4（`github_search`） |
| `fetch.sh` 薄包装、workflow 不变 | Task 4 |
| 本地连跑两次验证不重复 | Task 4 Step 6-7 |
| 台账缺失/损坏回退验证 | Task 4 Step 8 |
| workflow 会提交台账 | Task 4 Step 9 |
| README 数据源说明 | Task 5 |

无遗漏。

**2. Placeholder scan**

无 TBD / TODO / "add error handling" 之类占位；每个代码步骤都给了完整可粘贴代码。

**3. Type consistency**

- `load_seen`/`save_seen` 的 dict 结构（`{"github": [...], "mcp": [...]}`）在 Task 1 定义，Task 4 一致使用。
- `select_new(candidates, seen, limit)` 三参签名在 Task 3 定义与测试，Task 4 以位置参数调用一致。
- `render_document(today, sections)` 中 `sections` 为 `(title, source, body_lines)` 三元组，Task 3 测试与 Task 4 调用一致。
- `parse_mcpso` 返回项字段 `slug/name/author/added` 在 Task 2 定义，Task 3 `render_mcp_line` 与 Task 4 一致使用。
- `github_search(query, token, per_page)` 签名在 Task 4 定义，Task 4 测试的打桩函数同签名。

一致，无冲突。
