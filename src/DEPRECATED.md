# DEPRECATED — src/ 目录

此目录下的所有代码（CLI、TUI、Agent、Scraper）已被 `backend/` 取代，不再维护。

## 当前 source of truth

| 组件 | 旧路径 | 新路径 |
|------|--------|--------|
| Agent 逻辑 | `src/jobseeking_agent/agents/` | `backend/app/agents/` |
| Scraper | `src/jobseeking_agent/scrapers/` | `backend/app/scrapers/` |
| 数据模型 | `src/jobseeking_agent/models/` | `backend/app/models/` |
| 调度器 | `src/jobseeking_agent/scheduler.py` | `backend/app/scheduler.py` |
| 前端入口 | CLI / TUI | React (`frontend/`) |

## 为何保留而非删除

`src/` 的 `agents/tailor.py` 现为 re-export shim，指向 `backend/app/agents/tailor.py`。
直接删除会导致 `cli.py` 和 `tui/` 在 import 时报 `ModuleNotFoundError`。
由于 src/ 以独立进程运行（CLI 命令），不会与 FastAPI server 产生 SQLModel metadata 冲突。
见 `DECISIONS.md` — DEC-01。

## 不要修改此目录

任何新功能、bug fix 均应在 `backend/` 中进行。
