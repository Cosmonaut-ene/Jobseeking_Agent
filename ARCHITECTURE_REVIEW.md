# Jobseeking Agent — 项目全面审查报告

**审查日期**：2026-07-29
**审查分支**：`fix/engineering-quality`（领先 `main` 2 个提交，尚未合并）
**目的**：为后续升级开发提供完整的前后端结构、接口清单与已知问题清单

---

## 1. 项目概览

一个个人使用的 AI 求职自动化平台。核心流程：**爬虫抓岗位 → Gemini 评分匹配 → 高分即时推送 → 定制简历/求职信 → 追踪投递状态**。

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | FastAPI + SQLModel + SQLite | `backend/app/` |
| 前端 | React 18 + TypeScript + Vite + Tailwind | `frontend/src/` |
| AI | Gemini 2.5 Flash（`google-genai`） | 4 个 Agent：Scout / Tailor / Parser / CoverLetter |
| 爬虫 | Playwright（Seek）+ httpx/BS4（LinkedIn guest API） | **Indeed 未实现**（见 §5） |
| 定时任务 | APScheduler | 每天 AEDT 9:00 触发 |
| 通知 | HTTP Webhook（Telegram / Discord 兼容） | |
| 文件生成 | WeasyPrint+Jinja2（PDF）、python-docx（Word） | |

数据落地：`data/db/jobseeking.db`（SQLite）+ `data/user_profile.json`（简历画像，**不进 DB**）+ `data/resumes/` + `data/cover_letters/`。

---

## 2. 后端架构

### 2.1 入口与启动流程 — `backend/app/main.py`

- `lifespan`：启动时 `init_db()` 建表 → `start_scheduler()` 启动 APScheduler；关闭时 `stop_scheduler()`。
- CORS 仅放行本地开发地址（5173/8000 的 localhost/127.0.0.1）。
- 7 个路由模块统一挂载在 `/api` 前缀下。
- 若 `frontend/dist` 存在则托管 SPA 静态资源（生产模式单体部署）。

### 2.2 配置 — `backend/app/config.py`
纯环境变量读取，无校验/默认值 fallback 逻辑之外的健壮性处理。路径常量（`DATA_DIR`/`DB_PATH`/`RESUMES_DIR` 等）集中于此。

### 2.3 数据模型 — `backend/app/models/`

| 模型 | 存储 | 关键字段 |
|---|---|---|
| `Job` | SQLite | `source`(linkedin/seek/indeed/manual)、`match_score`、`gap_analysis`(JSON，完整 5 段评估)、`status`(枚举：new→reviewed→dismissed/applied→interview→rejected/offer)、`notification_sent` |
| `ResumeVersion` | SQLite | `job_id` FK、`content_json`(定制后简历)、`ats_score`、`changes_summary` |
| `Application` | SQLite | `job_id`/`resume_version_id` FK、`channel`、`follow_up_date`、`status`(默认 `"pending"`，**全代码库无任何地方会更新它**，见 §5) |
| `UserProfile` | **JSON 文件**，非 DB | Pydantic 模型；`to_prompt_text()` 把画像拼成给 LLM 的 prompt |

### 2.4 路由层 — `backend/app/routers/`

#### `jobs.py`（岗位主流程）
| Method | Path | 功能 |
|---|---|---|
| GET | `/api/jobs` | 列表（按 status / min_score 过滤） |
| GET | `/api/jobs/{id}` | 详情 + 关联的 resume_versions |
| POST | `/api/jobs/scout` | 手动粘贴 JD → ScoutAgent 评分（不推送） |
| PUT | `/api/jobs/{id}/status` | 更新状态 |
| DELETE | `/api/jobs/{id}` | 删除 |
| POST | `/api/jobs/{id}/tailor` | 生成定制简历（TailorAgent）+ 生成 PDF |
| GET | `/api/jobs/{id}/cover-letter` | 读取已生成的求职信文件 |
| POST | `/api/jobs/{id}/cover-letter` | 生成求职信 + 记录 Application（status 固定为 `easy_apply` channel，7 天后 follow-up） |

#### `profile.py`（简历画像）
`GET/PUT /api/profile`、`POST /api/profile/upload-resume`（文件解析）、`POST /api/profile/parse-resume`（文本解析）— 均走 `ResumeParser` Agent。

#### `settings.py`
`GET/POST /api/settings`、`POST /api/settings/key`、`GET /api/settings/status`。**直接读写项目根目录的 `.env` 文件**（字符串替换 + 落盘），并同步 `os.environ`。

#### `notifications.py`
`POST /api/notifications/test`（webhook 测试）、`POST /api/notifications/trigger-scout`（后台线程触发一次全量爬取+评分）、`GET /api/notifications/tasks/{id}`（轮询任务状态）。

#### `scrapers.py`
`POST /api/scrapers/seek`、`POST /api/scrapers/linkedin`、`GET /api/tasks/{id}`、`DELETE /api/tasks/{id}`（取消）。采用**进程内内存字典 `_tasks` + 后台线程**做异步任务管理（非 Celery/队列），**无持久化，重启进程后任务状态全部丢失**。

#### `dashboard.py`
`GET /api/dashboard/stats`、`GET /api/dashboard/recent-jobs`、`GET /api/dashboard/advisor`（AI 顾问报告，基于历史 `gap_analysis` 统计高频缺失技能）、`GET /api/dashboard/followups`（逾期跟进列表）。

#### `files.py`
`GET /api/files/{id}/resume.pdf` — 仅此一个文件下载接口（**无 `.docx` 下载接口**，见 §5）。

### 2.5 AI Agents — `backend/app/agents/`

| Agent | 职责 | 关键约束 |
|---|---|---|
| `ScoutAgent` | 解析 JD 结构化字段 + 生成 5 段式匹配评估（ats_pct/strong_matches/missing_skills/…/recommendations），按阈值自动丢弃/推送 | `MID_SCORE_THRESHOLD` 以下直接丢弃不落库 |
| `TailorAgent` | 基于 JD + gap_analysis 重写 summary/skills/projects bullets，并二次调用 LLM 评估定制后 ATS 分 | 系统提示词要求 bullet 必须可溯源到 `source_raw`，**但当前代码没有任何服务端校验/过滤逻辑**（见 §5） |
| `ResumeParser` | PDF/DOCX/TXT/纯文本 → 结构化 UserProfile JSON | 明确要求不得编造字段 |
| `CoverLetterAgent` | 生成 subject + 3 段正文求职信，落盘为 txt | 仅引用画像中真实存在的项目/技能 |

四个 Agent 都直接 `genai.Client(...)` 同步调用，无重试/超时封装，无速率限制处理。

### 2.6 爬虫 — `backend/app/scrapers/`

- **`seek.py`**：Playwright 同步 API，按 role×location 组合搜索，`_delay()` 随机 sleep 防封。已改为 path-based URL（`/xxx-jobs/in-All-Sydney-NSW/full-time`）。
- **`linkedin_guest.py`**：无需登录，调用 LinkedIn 对外公开的 guest API（`jobs-guest/jobs/api/...`），httpx 异步 + BeautifulSoup 解析。
- **`scheduler.py`**（`scrapers/` 下，业务逻辑）：`run_daily_scout()` 依次跑 Seek + LinkedIn，评分、分类 high/mid，最后发日报。**LinkedIn 请求失败/整体失败仅记日志，不推送失败告警**（PROJECT_STATE.md 中 PR #14 "调度失败 Discord 告警" 未合并，与代码现状一致）。
- **`scheduler.py`**（`backend/app/`，APScheduler 包装）：注意**同名但目录不同的两个 scheduler.py**，容易在阅读/搜索代码时混淆，建议后续重命名（如 `run_scheduler.py` vs `daily_job.py`）。

### 2.7 通知 — `backend/app/notifications.py`
`_send()` 根据 URL 是否包含 `discord.com/api/webhooks` 自动切换 payload 格式（Discord 用纯文本去 HTML 标签，其余按 Telegram Bot API 格式）。`push_high_score_job` / `push_daily_summary` 两个场景化封装。

### 2.8 文件生成
- **`pdf_generator.py`**：Jinja2 渲染 `templates/resume.html` → WeasyPrint 转 PDF。
- **`docx_generator.py`**：纯 `python-docx` 手工排版（无外部二进制依赖），提供 `generate_base_resume()` 和 `generate_tailored_resume()` 两个函数——**但 `generate_tailored_resume()` 目前没有被任何路由调用**（见 §5，前后端关于 docx 下载的功能存在明显断层）。

---

## 3. 前端架构

### 3.1 路由与导航
`App.tsx` 注册 8 个路由：`/`(Dashboard)、`/scout`、`/scrapers`、`/jobs`、`/resume`、`/profile`、`/notifications`、`/settings`。

`Layout.tsx` 侧边栏导航仅列出 **7 项**（Dashboard/Jobs/Scrapers/Notifications/Profile/Resume/Settings）——**`/scout` 页面存在但无入口可达**（见 §5）。

### 3.2 各页面职责

| 页面 | 功能 | 备注 |
|---|---|---|
| `Dashboard.tsx` | 状态统计卡片、逾期跟进表、AI Advisor 报告（按需生成） | |
| `Jobs.tsx` | 岗位列表+详情面板：审批/丢弃、Tailor、下载 Word、生成求职信、展开完整评估/原文 | 最核心的操作页 |
| `Scout.tsx` | 单条 JD 粘贴分析 | **与 Scrapers 页"手动粘贴"区块功能完全重复**，且无导航入口 |
| `Scrapers.tsx` | 手动粘贴分析 + Seek 定向爬取 + LinkedIn 定向爬取，任务轮询状态持久化（`sessionStorage` + 模块级 `store` Map，跨页面切换不丢失轮询） | 工程实现比较讲究 |
| `Resume.tsx` | 粘贴/上传简历 → 解析 → **增量合并**保存到 UserProfile（技能取 years 较大值、经历/项目/教育按 key 去重合并，占位符如 "N/A" 会被过滤不覆盖已有数据） | 合并逻辑写得细致，是本项目的亮点之一 |
| `Profile.tsx`（628 行，最大文件） | 6 个 Tab 编辑器：Basic / Skills / Experience / Projects / Education / Preferences | |
| `Notifications.tsx` | 手动触发一次全量爬取（daily scout）+ webhook 测试 | 展示 `task.result.scraped.indeed`，但后端 `run_daily_scout()` 返回的 stats 里根本没有 `indeed` 字段（见 §5） |
| `Settings.tsx` | API Key / Webhook / 阈值 / 调度时间配置 | 有一处过时错误提示引用了旧路径 `web.backend.main:app`（见 §5） |

### 3.3 共享组件
- **`EvaluationReport.tsx`**：折叠式渲染 5 段评估报告，各子 section 独立展开/收起，字段缺失时有 fallback 文案。
- **`JobCard.tsx`**：列表卡片，状态色 + 匹配度徽章 + 技能标签（超 4 个折叠为 "+N"）。
- **`Layout.tsx`**：固定宽度侧边栏（`w-52`），**无响应式/移动端适配**（无汉堡菜单、无 breakpoint 折叠逻辑）。

### 3.4 Context
- **`ThemeContext.tsx`**：light/dark，读取 `localStorage` 或系统偏好，切换时 toggle `<html>` 的 `dark` class。
- **`LanguageContext.tsx`**：en/zh 双语，`translations.ts` 集中管理所有文案 key，`navigator.language` 自动探测默认语言。

### 3.5 API Client — `frontend/src/api/client.ts`
纯 axios 实例 + TypeScript 接口定义（`Job`/`ResumeVersion`/`Application`/`UserProfile`/... ）。**没有统一的错误拦截器**，每个页面各自 try/catch 解析 `e.response.data.detail`，存在少量重复代码。

---

## 4. 完整 API 接口清单

| 分类 | Method | Path |
|---|---|---|
| Jobs | GET | `/api/jobs` |
| Jobs | GET | `/api/jobs/{id}` |
| Jobs | POST | `/api/jobs/scout` |
| Jobs | PUT | `/api/jobs/{id}/status` |
| Jobs | DELETE | `/api/jobs/{id}` |
| Jobs | POST | `/api/jobs/{id}/tailor` |
| Jobs | GET | `/api/jobs/{id}/cover-letter` |
| Jobs | POST | `/api/jobs/{id}/cover-letter` |
| Profile | GET/PUT | `/api/profile` |
| Profile | POST | `/api/profile/upload-resume` |
| Profile | POST | `/api/profile/parse-resume` |
| Settings | GET/POST | `/api/settings` |
| Settings | POST | `/api/settings/key` |
| Settings | GET | `/api/settings/status` |
| Notifications | POST | `/api/notifications/test` |
| Notifications | POST | `/api/notifications/trigger-scout` |
| Notifications | GET | `/api/notifications/tasks/{id}` |
| Scrapers | POST | `/api/scrapers/seek` |
| Scrapers | POST | `/api/scrapers/linkedin` |
| Scrapers | GET/DELETE | `/api/tasks/{id}` |
| Dashboard | GET | `/api/dashboard/stats` \| `recent-jobs` \| `advisor` \| `followups` |
| Files | GET | `/api/files/{id}/resume.pdf` |

**共 22 个接口**，均无鉴权（个人本地/单用户工具，符合当前定位）。

---

## 5. 已发现的问题清单（供升级前优先处理）

> 以下均为对照代码实际状态核实后的发现，非猜测。

1. **前后端功能断层：Word 简历下载不可用。**
   `frontend/src/pages/Jobs.tsx` 依赖 `job.has_docx`/`resume.docx_download_url` 和 `GET /api/files/{id}/resume.docx`；但 `backend/app/routers/jobs.py` 的 `tailor_job()` 只生成 PDF，从不调用 `docx_generator.generate_tailored_resume()`；`files.py` 也没有 `.docx` 路由。`docx_generator.py` 本身功能完整（含精美排版），只是没有被接入。→ **修复成本低、价值高**，是最值得优先补的一个 Task。

2. **依赖清单缺失 `weasyprint` 和 `jinja2`。**
   `pdf_generator.py` 直接 `import weasyprint`/`jinja2`，但 `pyproject.toml`、`backend/requirements.txt`、`uv.lock` 均无记录。全新环境按 README 步骤安装后，Tailor 接口的 PDF 生成会静默失败（有 try/except 兜底，只记 warning，不影响主流程，但用户会发现 PDF 一直生成不出来）。

3. **Tailor 的 `source_raw` 反幻觉校验未接入主干。**
   `DECISIONS.md` DEC-02 描述了 `_validate_bullets()`（检测新增数字，防止 LLM 编造数据），但当前 `backend/app/agents/tailor.py` 里没有这个函数——对应 `PROJECT_STATE.md` 里"待合并 PR #12"，说明这是**已开发但未合并**，不是代码回归。合并顺序上建议优先处理。

4. **Scraper 重试机制未接入主干。** 同上，对应待合并 PR #13（Seek/LinkedIn 重试 + 失败日志），当前 `seek.py`/`linkedin_guest.py` 只有 try/except 跳过，没有指数退避重试。

5. **调度失败无告警。** 对应待合并 PR #14。当前 `backend/app/scheduler.py._daily_job()` 失败只记日志，用户不会收到任何提醒（除非主动打开日志）。

6. **`Application.status` 是死字段。** 创建时固定为 `"pending"`，全代码库找不到任何地方会把它更新为 `applied`/`responded`/`interview`（`Job.status` 才是真正在用的状态机）。而 `dashboard.py` 的 `get_advisor_report()` 却基于 `Application.status` 统计 `response_rate`——这段统计逻辑目前**永远输出 0**，属于隐藏 bug。建议要么把 Application 状态机接起来，要么把这段死逻辑从 Advisor 报告里移除。

7. **`/scout` 页面孤立。** `Scout.tsx` 与 `Scrapers.tsx` 顶部"手动粘贴分析"区块功能重复（都是 `POST /api/jobs/scout`），且 `Layout.tsx` 侧边栏没有链接到 `/scout`，只能靠直接改 URL 访问。建议二选一：删除 `Scout.tsx` 或把它合并为 Scrapers 的独立入口。

8. **Indeed 只存在于文案，不存在于代码。** README、`Job.source` 字段注释、`Scout.tsx`/`Scrapers.tsx` 下拉框选项、`Notifications.tsx` 的 `task.result.scraped.indeed` 展示都提到 Indeed，但 `backend/app/scrapers/` 下没有 `indeed.py`，也没有 `/api/scrapers/indeed` 路由。`run_daily_scout()` 返回的 stats dict 也只有 `{seek, linkedin}`，前端读 `.indeed` 会渲染成 `undefined`。这是文档/UI 承诺与实现不一致，需要明确：要么实现 Indeed 爬虫，要么把相关 UI/文案清理掉。

9. **两个同名 `scheduler.py`。** `backend/app/scheduler.py`（APScheduler 包装）与 `backend/app/scrapers/scheduler.py`（实际业务逻辑 `run_daily_scout`）职责不同但命名相同，全局搜索/新人理解成本较高，建议改名。

10. **任务状态纯内存存储，无持久化。** `scrapers.py`/`notifications.py` 里的 `_tasks: dict` 是进程内全局变量，配合后台线程。一旦 uvicorn 因为 `--reload` 重启或进程崩溃，所有进行中任务状态丢失，前端轮询会收到 404。个人工具场景下影响有限，但如果要支持多 worker 部署或前端断线重连体验，需要换成 Redis/DB 持久化。

11. **`Settings.tsx` 里有过时的错误提示文案**（第 55 行）："Cannot reach server... `uv run uvicorn web.backend.main:app --reload`"，引用的是被 `web/` 目录取代前的旧入口路径，与现在的 `uvicorn backend.app.main:app` 不符，属于遗留文案未清理。

12. **`web/` 遗留目录仍存在于仓库中。** `web/backend/` + `web/frontend/` 是被 `backend/`+`frontend/` 取代的旧版本（据 memory 记录），`src/` 目录已有 `DEPRECATED.md` 明确标注但 `web/` 没有类似标注，建议补一份说明或直接清理（先确认没有脚本/CI 引用它）。

13. **TailorAgent 只重写 Projects bullets，不重写 Experience bullets。** `TailorAgent._tailor()` 的 `TAILOR_SCHEMA` 只有 `tailored_projects`，`experience` 是从 `user_profile.experience` 原样透传（`agents/tailor.py` 第 92-100 行）。如果用户的核心亮点在工作经历而非个人项目，Tailor 功能对他们的实际提升有限，属于功能范围而非 bug，值得在下一轮开发中讨论是否扩展。

---

## 6. 未合并分支一览（来自 `git branch -a`）

`main` 之外还有 12 个本地分支和若干远程专属分支未合并，其中与 `PROJECT_STATE.md`"待合并 PR"对应的 4 个（`refactor/tailor/unify-implementations`、`feat/tailor/source-raw-validation`、`feat/scrapers/add-retry`、`feat/scheduler/failure-alerts`）是当前最优先级；另有 `feat/discord-webhook`、`feat/i18n`、`feat/tailor/ats-keyword-injection`、`fix/resume-incremental-merge`、`fix/resume-parser-placeholder` 等分支，需要确认是否已通过其他方式合入 main（部分功能如 i18n/dark-mode/docx-generator 从代码现状看已经在 main 上，可能是分支已合并但未删除，建议清理陈旧分支）。

---

## 7. 后续开发建议（按优先级）

**P0（修复现有断层，成本低价值高）**
1. 把 `docx_generator.generate_tailored_resume()` 接入 `tailor_job()` 路由 + 新增 `/api/files/{id}/resume.docx`，修复 Word 下载功能。
2. 补齐 `weasyprint`/`jinja2` 到依赖清单。
3. 清理 `Application.status` 死逻辑，或把它真正接入 Job 状态变化。
4. 合并 PR #11-14（Tailor 统一实现 / source_raw 校验 / scraper 重试 / 调度失败告警）。

**P1（体验/一致性）**
5. 决定 `/scout` 页面去留；决定 Indeed 是否要真正实现或从 UI/文案中移除。
6. 修复 `Settings.tsx` 过时错误提示；侧边栏补响应式支持（memory 中记录过"响应式侧边栏"需求，但当前代码未体现，需要重新确认是否要做）。
7. 重命名两个 `scheduler.py`，降低认知负担。

**P2（功能扩展，需先讨论范围）**
8. Tailor 扩展到 Experience bullets 重写。
9. 任务状态持久化（如迁移到 SQLite 表或轻量队列），为多进程部署做准备。
10. `web/` 遗留目录清理确认。

---

## 附：Memory 记录与代码现状的差异说明

此前会话记忆（MEMORY.md）中记录的 "v2.2 — job notes (F-notes) + 响应式侧边栏 (F-mobile)" 功能，经本次核实：`backend/app/models/job.py` 无 `user_notes` 字段、无 `PUT /api/jobs/{id}/notes` 路由、`Layout.tsx` 无移动端汉堡菜单逻辑。这两项功能**在当前 `fix/engineering-quality` 分支上不存在**，可能是记录于未合并分支或已被回退。后续开发前建议先确认这两项功能的真实状态，我会同步更新 memory 记录以避免下次误导。
