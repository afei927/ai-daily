#!/usr/bin/env bash
set -euo pipefail

DATE=$(date +%Y-%m-%d)
OUTDIR="daily"
mkdir -p "$OUTDIR"
OUTFILE="$OUTDIR/$DATE.md"

{
  echo "# AI Daily — $DATE"
  echo

  # ── 1. Smithery MCP Servers ──
  echo "## Trending MCP Servers (Smithery)"
  echo "Source: https://smithery.ai"
  echo
  curl -sL --max-time 15 "https://smithery.ai/servers" |
    grep -oP 'href="/servers/[^"]*"[^>]*>[^<]+' |
    head -20 |
    sed 's|href="/servers/||;s|"[^>]*>| |;s|</a>||' |
    while read -r slug name; do
      echo "- [$name](https://smithery.ai/servers/$slug)"
    done
  echo

  # ── 2. MCP.so New Arrivals ──
  echo "## New MCP Servers (MCP.so)"
  echo "Source: https://mcp.so/servers?sort=latest"
  echo
  curl -sL --max-time 15 "https://mcp.so/servers?sort=latest" |
    grep -oP 'href="/servers/[^"]*"[^>]*class="[^"]*font-semibold' |
    head -15 |
    sed 's|href="/servers/||;s|".*||' |
    while read -r slug; do
      echo "- [$(echo $slug | sed 's|-| |g')](https://mcp.so/servers/$slug)"
    done
  echo

  # ── 3. GitHub trending: ai-agent topics ──
  echo "## GitHub Trending: AI Agent Tools"
  echo "Source: https://github.com/topics/ai-agent"
  echo
  for page in 1 2; do
    curl -sL --max-time 15 "https://github.com/topics/ai-agent?page=$page" |
      grep -oP 'href="/[^/"]*/[^/"]*"[^>]*data-view-component="true" class="text-bold"' |
      sed 's|href="/||g;s|".*||' |
      head -10 |
      while read -r repo; do
        stars=$(curl -sL --max-time 10 "https://api.github.com/repos/$repo" | grep -oP '"stargazers_count":\K[0-9]+' | head -1)
        echo "- [$repo](https://github.com/$repo) ⭐ $stars"
      done
  done
  echo

  # ── 4. GitHub trending: mcp-server ──
  echo "## GitHub Trending: MCP Servers"
  echo "Source: https://github.com/topics/mcp-server"
  echo
  for page in 1 2; do
    curl -sL --max-time 15 "https://github.com/topics/mcp-server?page=$page" |
      grep -oP 'href="/[^/"]*/[^/"]*"[^>]*data-view-component="true" class="text-bold"' |
      sed 's|href="/||g;s|".*||' |
      head -10 |
      while read -r repo; do
        stars=$(curl -sL --max-time 10 "https://api.github.com/repos/$repo" | grep -oP '"stargazers_count":\K[0-9]+' | head -1)
        echo "- [$repo](https://github.com/$repo) ⭐ $stars"
      done
  done
  echo

  # ── 5. MCP.so Skills ──
  echo "## Agent Skills (MCP.so)"
  echo "Source: https://mcp.so/skills"
  echo
  curl -sL --max-time 15 "https://mcp.so/skills" |
    grep -oP 'href="/skills/[^"]*"[^>]*>[^<]+' |
    head -10 |
    sed 's|href="/skills/||;s|".*>| |;s|</a>||' |
    while read -r slug name; do
      echo "- [$name](https://mcp.so/skills/$slug)"
    done
  echo

} > "$OUTFILE"

echo "Written: $OUTFILE"
