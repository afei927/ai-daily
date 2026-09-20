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


_CARD_SPLIT = re.compile(r'<a href="/servers/([^"/]+)"')
_H3 = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)
_AUTHOR = re.compile(
    r'<p\s[^>]*class="(?=[^"]*text-xs)(?=[^"]*truncate)[^"]*"[^>]*>(.*?)</p>', re.S)
_ADDED = re.compile(r'<span class="ml-auto shrink-0"[^>]*>(.*?)</span>', re.S)
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
    os.makedirs(OUTDIR, exist_ok=True)
    outfile = os.path.join(OUTDIR, f"{today}.md")
    if os.path.exists(outfile) and not os.environ.get("AI_DAILY_FORCE"):
        print(f"Skip: {outfile} already exists "
              f"(set AI_DAILY_FORCE=1 to regenerate)")
        return 0

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

    with open(outfile, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Written: {outfile}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
