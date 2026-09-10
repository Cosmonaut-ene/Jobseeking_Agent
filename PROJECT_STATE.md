# PROJECT_STATE.md

**最后更新**：2026-09-10（代码级重新核实，替换此前 v1 时代的过期快照）
**当前阶段**：v3 SPEC 驱动重写后，功能完整，253 个后端测试全绿

---

## 重要说明：本文件此前严重过期

上一版 PROJECT_STATE.md（2026-04-09）描述的是 v3 升级前（v1）的状态，其中"待合并 PR #11-14""APScheduler 每日定时""Scraper 有重试"等条目，在 2026-08-19 的 v3 重写（见 DECISIONS.md DEC-05~07）之后已不再成立——v1 的这些 PR/分支实际停留在已废弃的 `main`/`master` 历史线上，从未合入当前实际开发的分支线（`docs/spec/v3-upgrade`，已推进到 PR #28）。本次更新基于**实际代码 + git log + 真实 pytest 运行结果**核实，不是转述旧文档。

---

## 系统状态（代码级核实，2026-09-10）

| 组件 | 状态 | 备注 |
|------|------|------|
| FastAPI 后端 | ✅ 运行中 | `backend/app/main.py`，10 个 router，43 个端点（实测 `@router.(get|post|...)` 计数） |
| React 前端 | ✅ 构建正常 | `frontend/`，`tsc --noEmit` 通过，无编译错误 |
| SQLite 数据库 | ✅ 正常 | `data/db/jobseeking.db`；无 Alembic，`create_all` + 手写幂等 startup 数据修复（如 legacy status 迁移） |
| 后台定时调度 | ❌ 已移除（非缺陷，是设计决策） | TASK-A01（PR #20）移除 APScheduler，全面改为手动触发；`scrapers/scheduler.py` 已重命名为 `scrapers/batch_scrape.py` |
| Seek Scraper | ✅ 正常，**无重试逻辑** | `backend/app/scrapers/seek.py`；v1 时代曾有 tenacity 重试（PR #13），该分支从未合入当前代码线 |
| LinkedIn Guest Scraper | ✅ 正常，**无重试逻辑** | 同上，`linkedin_guest.py` |
| Indeed Scraper | ❌ 不存在 | 仅在 `Job.source` 字段注释和 dashboard 分组里留有字符串引用，无实际抓取实现；README 已据此更正 |
| Scout Agent | ✅ 正常 | Gemini 2.5 Flash，5 段结构化评估报告 |
| 确定性 ATS 评分引擎 | ✅ 正常 | `backend/app/ats/`：`keyword_match.py`（regex + 词边界，含别名表）+ `parseability.py`，`simulator.py` 用固定公式 `parseability*0.6 + keyword_match*0.4`，与 LLM 自评分完全分离 |
| Tailor Agent（evaluator-optimizer 循环） | ✅ 正常 | `backend/app/agents/tailor.py`；最多 `TAILOR_MAX_ITERATIONS=2` 轮，用确定性关键词分数（非 LLM）作为停止信号，达到 `TAILOR_DETERMINISTIC_THRESHOLD=80` 或无更多缺失关键词即提前退出 |
| GitHub MCP 集成 | ✅ 正常 | `backend/app/mcp/github_client.py`，走官方远程 endpoint；两个真实 bug（EmbeddedResource 解析、ExceptionGroup 解包）已修复并有回归测试 |
| GitHub Profile Sync Agent | ✅ 正常 | `backend/app/agents/profile_sync.py`：从真实 GitHub 数据推断技能栈+年限，生成 diff，人工确认后才写入 |
| 应用状态机（Application） | ✅ 正常，**真实枚举转移表** | `ready → applied → {responded, interview, rejected}`，非法转移返回 HTTP 400；`Job.status` 是另一个更粗粒度、无强制转移的字段，不要混淆两者 |
| Cover Letter Agent | ✅ 正常 | 文件存储于 `data/cover_letters/`，无 DB 关联 |
| 通知系统 | ✅ 正常，reminder-only | Discord/Telegram 兼容 webhook；投递确认摩擦成本已知悉（DEC-05），消息内不含可执行操作，确认固定在 App 内完成 |
| 分析 API | ✅ 正常 | `backend/app/routers/analytics.py`，6 端点，独立 `analytics_demo.db`，真实窗口函数/CTE/`json_each` |

---

## 真实测试结果（2026-09-10 实测，非文档转述）

```
PYTHONPATH=. python3 -m pytest backend/tests/ -q
253 passed, 3 warnings in 11.24s
```
253 个测试全部通过，0 失败。前端 `npx tsc --noEmit` 无类型错误。前端无独立测试套件（`package.json` 仅有 `dev`/`build`/`preview` 脚本）。

---

## 已知技术债

- `match_score` / ATS 阈值仍是配置项而非动态学习（`MID_SCORE_THRESHOLD`/`HIGH_SCORE_THRESHOLD`），未做用户维度验证
- Cover Letter 内容仅存文件系统，无 DB 追踪
- 无正式迁移框架（Alembic）——现状是手写幂等 startup 脚本，规模小尚可接受，规模变大需要重新评估
- `src/` CLI/TUI 层为 v1 遗留代码，已被 React 前端替代（`src/DEPRECATED.md` 已标注）
- 本地 `main`/`master` 分支停留在 v1 状态（含已废弃的 retry/Indeed/dark-mode 代码），与当前实际开发线（`docs/spec/v3-upgrade`，PR #28）完全脱节——**如果要长期维护这两条历史线共存的现状，建议尽快决定去留，避免未来又造成文档/分支双重过期**

---

## 下次 Session 建议起点

1. 决定 `main`/`master`/`v1-backup` 这几条历史分支的去留，避免继续制造"文档说的是另一条分支的状态"这类混乱
2. TASK-05（如仍要做）：Cover Letter 写入数据库
3. 补充正式迁移工具评估：项目规模是否已经到了值得引入 Alembic 的程度
