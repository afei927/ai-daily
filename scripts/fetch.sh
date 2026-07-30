#!/usr/bin/env bash

DATE=$(date +%Y-%m-%d)
OUTDIR="daily"
mkdir -p "$OUTDIR"
OUTFILE="$OUTDIR/$DATE.md"

echo "# AI Daily — $DATE" > "$OUTFILE"
echo >> "$OUTFILE"

# ── 1. GitHub: AI Agent 高星仓库 ──
echo "## AI Agent 高星仓库 (GitHub)" >> "$OUTFILE"
echo "Source: GitHub Search (stars:>500 topic:ai-agent)" >> "$OUTFILE"
echo >> "$OUTFILE"
curl -sL --max-time 15 \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=topic:ai-agent+stars:>500&sort=stars&order=desc&per_page=10" 2>/dev/null \
  | python3 -c "
import json,sys
try:
    data = json.load(sys.stdin)
    for item in data.get('items', [])[:10]:
        print(f\"- [{item['full_name']}]({item['html_url']}) ⭐ {item['stargazers_count']} — {item.get('description','')[:80] or 'No description'}\")
except: pass
" 2>/dev/null >> "$OUTFILE" || echo "- (failed to fetch)" >> "$OUTFILE"
echo >> "$OUTFILE"

# ── 2. GitHub: MCP Server 高星仓库 ──
echo "## MCP Server 高星仓库 (GitHub)" >> "$OUTFILE"
echo "Source: GitHub Search (stars:>100 topic:mcp-server)" >> "$OUTFILE"
echo >> "$OUTFILE"
curl -sL --max-time 15 \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=topic:mcp-server+stars:>100&sort=stars&order=desc&per_page=10" 2>/dev/null \
  | python3 -c "
import json,sys
try:
    data = json.load(sys.stdin)
    for item in data.get('items', [])[:10]:
        print(f\"- [{item['full_name']}]({item['html_url']}) ⭐ {item['stargazers_count']} — {item.get('description','')[:80] or 'No description'}\")
except: pass
" 2>/dev/null >> "$OUTFILE" || echo "- (failed to fetch)" >> "$OUTFILE"
echo >> "$OUTFILE"

# ── 3. GitHub: awesome-mcp-servers ──
echo "## Awesome MCP Servers 集合" >> "$OUTFILE"
echo "Source: popular awesome-list repos" >> "$OUTFILE"
echo >> "$OUTFILE"
for repo in "punkpeye/awesome-mcp-servers" "appcypher/awesome-mcp-servers" "talent-bird/awesome-mcp"; do
  data=$(curl -sL --max-time 10 "https://api.github.com/repos/$repo" 2>/dev/null)
  stars=$(echo "$data" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('stargazers_count','?'))" 2>/dev/null)
  desc=$(echo "$data" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('description','')[:80])" 2>/dev/null)
  echo "- [$repo](https://github.com/$repo) ⭐ $stars — $desc" >> "$OUTFILE"
done
echo >> "$OUTFILE"

# ── 4. Agent Skills (MCP.so skills 页面) ──
echo "## Agent Skills" >> "$OUTFILE"
echo "Source: https://mcp.so/skills" >> "$OUTFILE"
echo >> "$OUTFILE"
curl -sL --max-time 15 "https://mcp.so/skills" 2>/dev/null \
  | sed -n 's/.*href="\/skills\/\([^"]*\)".*title="\([^"]*\)".*/\1 \2/p' \
  | head -20 \
  | while read -r slug title; do
      echo "- [$title](https://mcp.so/skills/$slug)" >> "$OUTFILE"
    done
echo >> "$OUTFILE"

# ── 5. 新发布 MCP Servers (MCP.so) ──
echo "## 新发布 MCP Servers (MCP.so)" >> "$OUTFILE"
echo "Source: https://mcp.so/servers?sort=latest" >> "$OUTFILE"
echo >> "$OUTFILE"
curl -sL --max-time 15 "https://mcp.so/servers?sort=latest" 2>/dev/null \
  | sed -n 's/.*href="\/servers\/\([^"]*\)".*>\([^<]*\)<\/a>.*/\1 \2/p' \
  | head -15 \
  | while read -r slug name; do
      echo "- [$name](https://mcp.so/servers/$slug)" >> "$OUTFILE"
    done
echo >> "$OUTFILE"

echo "Written: $OUTFILE"
