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
