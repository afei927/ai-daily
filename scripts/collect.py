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
    r'<p\s[^>]*class="[^"]*text-muted-foreground[^"]*"[^>]*>(.*?)</p>', re.S)
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
