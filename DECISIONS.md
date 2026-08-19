# DECISIONS.md

记录本项目重要的设计决策，防止被重新引入。

---

## 2026-03-30 — 工程质量改进 session

### DEC-01: Tailor 合并策略：shim 而非删除

**决策**：`src/jobseeking_agent/agents/tailor.py` 改为 re-export shim，而非直接删除。

**原因**：
- src/ CLI/TUI 和 backend/ 共享同一 SQLite 文件，但两套 SQLModel 模型类在同一 Python 进程中会产生 metadata 冲突
- src/ 模块以独立进程运行（CLI 命令），与 FastAPI server 进程完全隔离，因此 shim 方案无运行时冲突
- 直接删除会导致 `cli.py` 和 `tui/screens/jobs.py` 在 import 时报 ModuleNotFoundError

**被拒绝的方案**：
- 直接删除 src/tailor.py + 更新两处 import 指向 backend：会在同一进程中同时加载两套 SQLModel 模型，引发 `Table already defined` 错误
- 完整迁移 cli.py/tui 到 backend 模型：scope 太大，超出本次任务

---

### DEC-02: source_raw 校验：仅检查数字，不阻断流程

**决策**：`_validate_bullets()` 只检测 rewritten 中新增的数字（`\d+`），不检测新增的技术词汇；检测到问题时记录 warning，不阻断 Tailor 输出。

**原因**：
- 检测新增技术词汇需要 NER/entity matching，成本高，误报率高（LLM 可能合理地改写技术词措辞）
- 数字（%, $, k, 年份）是 LLM 捏造的最常见形式，regex 可靠
- 阻断流程会导致边缘情况（如"3 years" → "3+ years"）打断正常使用

**被拒绝的方案**：
- 完全阻断含 warning 的 Tailor 结果：过于激进，会降低系统可用性

---

### DEC-03: Scraper 重试策略差异化

**决策**：LinkedIn 最多重试 3 次，Seek 最多 2 次。

**原因**：
- LinkedIn 用 httpx（轻量 async HTTP），重试成本低
- Seek 用 Playwright（Chromium），每次重试需要重新导航，资源消耗高
- Seek 仅对 `PlaywrightTimeoutError` 重试，其他错误（HTML 解析失败、元素缺失）重试意义不大

---

### DEC-04: 调度失败告警使用 lazy import

**决策**：`scheduler.py` 的 except 块中用局部 import 引入 `push_error_notification`，而非顶层 import。

**原因**：防止 scheduler ↔ notifications 之间的循环依赖风险；同时将通知相关代码的加载推迟到真正需要时。

---

## 2026-08-19 — v3.0 升级 session

### DEC-05: 投递确认放弃"消息内一键操作"，改为推送提醒 + App 内确认

**决策**：SPEC 附录 F.6 TASK-D02 原方案是"推送消息里放一键确认按钮/链接，零摩擦、不用回 App"。改为推送只做提醒（纯文案，不含任何可执行操作），确认动作固定在 App 内针对具体 Job 完成。

**原因**：
- 实测发现用户实际配置的通知 webhook 是纯 Discord webhook（`NOTIFICATION_WEBHOOK_URL` 含 `discord.com`，无 `NOTIFICATION_CHAT_ID`）。Discord 的交互按钮需要注册完整 Discord Application（slash commands + interaction endpoint + Ed25519 签名验证），普通 webhook 做不到。
- 退一步的方案（消息里放 magic link，点了直接调后端接口）对当前 Web 服务架构可行，但与附录 F.5 模块 A（本地桌面化，无公网暴露面）直接冲突——手机上刷到推送、点链接，够不着笔记本上跑的 `localhost` 服务。除非做内网穿透，但那会抵消桌面化本来想要的安全收益（消除公网暴露面）。
- 用户直接拍板：接受"确认需要回 App"这个摩擦成本，换取方案在当前架构和未来桌面化架构下都成立，不需要模块 A 落地后重做。

**被拒绝的方案**：
- Telegram 风格 inline keyboard：技术上可行但用户用的是 Discord，不适用；且引入"按 webhook 类型分叉不同确认机制"的复杂度，不划算
- Magic link 免登录确认：见上，与模块 A 冲突
- 完整 Discord Bot Application（slash commands + interaction endpoint）：工作量与收益不成比例，且需要一个公网可达的 interaction endpoint，同样与桌面化方向冲突

---

### DEC-06: GitHub MCP 走远程 endpoint，不走本地 Docker；`list_repos`/`get_repo_languages` 无直接对应工具，用替代方案实现

**决策**：TASK-B01 用 GitHub 官方远程 MCP server（`https://api.githubcopilot.com/mcp/`，HTTP/SSE，`Authorization: Bearer <PAT>`），不用本地 Docker 镜像（`ghcr.io/github/github-mcp-server`）。`list_repos()` 用 `search_repositories(query="user:<username>")` 代替（无直接的 list-repos 工具）；`get_repo_languages()` 用 `get_file_contents(path="")` 读根目录 + 文件名后缀启发式代替（无直接的语言统计工具）。

**原因**：
- 本机 Docker daemon 本身是坏的（`docker info` 直接 segfault），本地 Docker 传输方案在这个开发环境里走不通；远程 HTTP endpoint 不需要本地进程，绕开这个问题。
- GitHub 官方文档（`github/github-mcp-server` 的 README.md / docs/remote-server.md，人工核实、非本 agent 独立抓取）里 `repos` toolset 没有直接的"列出用户仓库"或"获取语言统计"工具；前者官方文档给出的等价做法就是 `search_repositories` 加 `user:` 限定符，后者没有现成替代，只能退化成目录列表 + 文件后缀名的启发式，精度低于真实的按字节数加权语言统计。
- **本次开发过程中没有可用的 GITHUB_TOKEN，也没确认到 `api.githubcopilot.com` 的出口网络权限，未做过一次真实的实时调用**——MCP Python SDK 的用法（`streamable_http_client`/`ClientSession`/`CallToolResult` 字段结构）是装了 `mcp==2.0.0` 包后针对已安装的 SDK 实测验证的，但"调用 GitHub 真实工具会返回什么"这件事没有验证过。TASK-B01 的 AC「四项调用均可返回真实数据」需要人工用真实 token 跑一遍才能算完成。

**被拒绝的方案**：
- 本地 Docker 镜像传输：Docker daemon 在开发环境里坏的，走不通
- 自己封装 GitHub REST API 代替 MCP：SPEC 明确禁止（"不得自行封装 GitHub REST API，必须走 MCP server"，本 Task 的目的之一就是验证工具可插拔性）
- 为 `get_repo_languages` 找不到直接工具就先跳过整个 B01：判断为不必要——三个功能齐全的工具（`get_me`/`search_repositories`/`get_file_contents`/`list_commits`）已经能覆盖 B02 大部分需求，语言统计用降级方案先跑起来，比整体阻塞划算
