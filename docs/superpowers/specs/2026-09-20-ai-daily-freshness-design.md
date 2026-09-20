# AI Daily 内容新鲜度改造 — 设计文档

日期：2026-09-20
状态：已确认（方案 A，常青榜 top 10）

## 问题

每日产物 `daily/YYYY-MM-DD.md` 内容几乎不变。对比 `2026-09-19.md` 与
`2026-09-20.md`，条目完全相同，只有 star 数在缓慢增长。

根因：

1. 第 1、2 段用 GitHub `sort=stars&order=desc` 取 top 10 —— 按总星数排名的
   榜单天然固定，名单不会变。
2. 第 3 段是 3 个写死的仓库，永远一样。
3. 第 4、5 段（mcp.so 的 Skills / 最新 MCP）**输出为空** —— `sed` 正则要求
   `>标题</a>` 出现在同一行，而页面 HTML 被压缩成单行，解析失败。
4. 脚本没有任何"已发布过"的记忆，因此不存在"新"的概念。

结论：当前产物是"一张几乎不变的静态榜单"，不是"每日资讯"。

## 目标

- 每日文件必须包含当天真正新的内容。
- 不重复：同一条目（在"新发现"区）最多出现一次，永不复读。
- 保留一个稳定的常青榜，供随时查阅当前头部项目。

## 非目标

- 不引入数据库、外部服务或前端。
- 不改动 GitHub Actions 的调度时间与触发方式。
- 不做 star 增速/trending 计算（需要长期历史数据，留待后续）。
- **本次移除**原脚本的 "Agent Skills"（`mcp.so/skills`）区块：其解析已失效且
  输出为空，本次不修复、直接删除。修复留待后续。

## 方案（方案 A：累计台账 + 宽窗口候选池）

### 为什么不是"只抓昨天之后创建的"

GitHub 搜索索引有延迟。若严格按 `created:>last_run` 切窗口，未被及时索引的
仓库会被永久漏掉。改为"宽窗口候选池 + 累计台账去重"：候选池足够宽以保证不漏，
台账保证不重。

### 供给端（已实测）

| 来源 | 查询/端点 | 实测结果 |
|------|-----------|----------|
| GitHub 新区 | `topic:ai-agent created:>7天` | ~850 条/周 |
| GitHub 新区 | `topic:mcp-server created:>7天` | 供给充足 |
| MCP 新区 | `https://mcp.so/servers?sort=latest` | 正常返回 60+ 条 `/servers/<slug>` |
| 常青榜 | GitHub `sort=stars&order=desc` | 稳定 |

注意：GitHub 仓库搜索**不支持按创建时间排序**（仅 stars / forks /
help-wanted-issues / updated）。因此需要先取一批（per_page=100），在脚本内
按 `created_at` 自行倒序。

### 文件结构

```
scripts/fetch.sh      # 入口，改为调用 python；workflow 无需改动
scripts/collect.py    # 抓取 / 解析 / 去重 / 渲染
state/seen.json       # 累计台账 {"github":[...], "mcp":[...]}
daily/YYYY-MM-DD.md   # 产物
```

`fetch.sh` 保持为入口（`.github/workflows/ai-daily.yml` 调用 `bash scripts/fetch.sh`），
内部改为 `python3 scripts/collect.py`，避免改动 workflow。

### 台账 `state/seen.json`

```json
{
  "github": ["owner/repo", "..."],
  "mcp": ["slug", "..."]
}
```

- 累计集合，永久去重。
- 每次运行把当次"新发现"区的条目写回。
- 文件缺失、为空或 JSON 损坏 → 视为空台账，不中断。

### 每日文件结构

```markdown
# AI Daily — YYYY-MM-DD

## 常青榜 · AI Agent (GitHub)
Source: GitHub Search (topic:ai-agent, sort by stars)
- <10 条，按 star 降序>

## 常青榜 · MCP Server (GitHub)
Source: GitHub Search (topic:mcp-server, sort by stars)
- <10 条，按 star 降序>

## 今日新发现 · GitHub
Source: GitHub Search (topic:ai-agent / mcp-server, created:>7d)
- <最多 10 条，近 7 天创建且台账中不存在>

## 今日新发现 · MCP Server
Source: https://mcp.so/servers?sort=latest
- <最多 10 条，mcp.so 最新且台账中不存在>
```

条目格式沿用现有风格：

```
- [owner/repo](https://github.com/owner/repo) ⭐ 12345 — 描述（截断到 80 字符）
```

### 各区块逻辑

**常青榜（2 个）**
- 查询：`topic:ai-agent stars:>500 sort=stars order=desc per_page=10`
  与 `topic:mcp-server stars:>100 sort=stars order=desc per_page=10`。
- 每天重复输出，这是预期行为（用户明确要求保留）。
- 写入台账（避免同一项目在"新发现"区重复出现；常青榜项目均已创建多年，
  与 `created:>7d` 天然不相交，写入只是双保险）。

**今日新发现 · GitHub**
1. 查询 `topic:ai-agent created:>7天` 与 `topic:mcp-server created:>7天`，
   `per_page=100`，按 stars 降序取候选。
2. 合并去重，在脚本内按 `created_at` 倒序。
3. 剔除台账中已存在的 `full_name`。
4. 取前 10。
5. 将入选的 `full_name` 写回台账。

**今日新发现 · MCP Server**
1. 抓取 `https://mcp.so/servers?sort=latest`，带 `User-Agent`。
2. 解析每张卡片（已实测的结构，非猜测）：
   - slug：`href="/servers/([^"/]+)"`
   - 名称：该卡片内 `<h3 class="truncate font-semibold ...">NAME</h3>`
   - 作者：`<p class="text-muted-foreground truncate text-xs">AUTHOR</p>`
   - 时间：`<span class="ml-auto shrink-0">Added in N hours</span>`
   实现方式：以 `<a href="/servers/...` 为分隔切分 HTML，每段内用上述正则取值，
   并对名称/作者做 HTML 实体解码。取不到名称时回退用 slug。
3. 剔除台账中已存在的 slug。
4. 取前 10，条目附加 "Added in ..." 时间信息。
5. 将入选 slug 写回台账。

### 边界处理

| 情况 | 行为 |
|------|------|
| 某区当天无新条目 | 写 `- (今日无新增)`，文件仍每天不同 |
| 首次运行、台账为空 | 靠"取前 10"封顶，不会一次性倒灌 |
| 台账文件缺失/损坏 | 视为空，继续执行 |
| 单个网络请求失败 | 该区写 `- (抓取失败)`，其余区块继续 |
| GitHub 索引延迟 | 7 天宽窗口 + 台账去重，不漏不重 |

### GitHub 认证

请求带上 `Authorization: Bearer $GITHUB_TOKEN`（Actions 环境已提供），
提高速率限额。本地未设置时自动省略该头，回退到匿名请求。

### 错误处理与退出码

- 脚本整体始终以 0 退出（除非 python 解释器缺失），保证 workflow 的
  commit 步骤能提交已抓到的部分。
- 不吞掉所有异常：解析失败时打印到 stderr，便于排查。

## 测试与验证

1. **本地连跑两次** `bash scripts/fetch.sh`：
   - 第二次"今日新发现"区必须为空，或与第一次完全不重叠。
   - 常青榜两次应一致（star 数允许微增）。
2. **台账检查**：`state/seen.json` 在两次运行后包含第一次入选的全部条目。
3. **删除台账再跑**：应重新产出 10 条，验证损坏/缺失回退路径。
4. **解析单测**：用保存的 `mcp.so` HTML 快照验证 slug/名称解析（可选用一个
   小的 `tests/` 目录或内联断言）。
5. **workflow 干跑**：本地 `git add .` 后确认 `state/seen.json` 与
   `daily/*.md` 都在待提交列表内。

## 风险

- **mcp.so 页面结构变更** → 解析再次失效。缓解：解析失败时输出
  `- (抓取失败)` 而非静默空白，便于发现。
- **GitHub 匿名限额（60/小时）** → Actions 中用 token 缓解；本地连跑两次
  共 4 次搜索请求，远低于限额。
- **"新发现"质量**：近 7 天的新仓库 star 普遍很低，可能出现低质量条目。
  这是"新鲜度优先"的必然取舍，接受。

## 后续（不在本次范围）

- star 增速 / trending 榜（需留存每日快照做 delta）。
- Smithery.ai trending 源（README 提及但当前脚本未实现）。
- 恢复 Skills 区块（重新实现 mcp.so/skills 解析后加回）。
