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
