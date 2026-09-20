# AI Daily

每天自动收集热度最高的 **AI Agent 工具、MCP Server** 信息。

- 每日 UTC 2:00（北京时间 10:00）自动更新
- 数据按日期归档在 `daily/` 目录

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

## 手动触发

在 GitHub Actions 页面点击 `Run workflow` 即可立即更新。

## 本地运行与测试

```bash
bash scripts/fetch.sh          # 生成 daily/YYYY-MM-DD.md
python3 -m unittest tests.test_collect -v   # 运行单元测试
```

