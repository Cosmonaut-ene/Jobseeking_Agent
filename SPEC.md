# 求职助手系统 — 产品规格说明书

**版本**：2.3
**状态**：已实现
**最后更新**：2026年3月11日
**作者**：Zhang

---

## 目录

1. [项目概述](#1-项目概述)
2. [功能需求](#2-功能需求)
3. [用户故事](#3-用户故事)
4. [技术架构](#4-技术架构)
5. [数据模型](#5-数据模型)
6. [API 设计](#6-api-设计)
7. [UI/UX 设计](#7-uiux-设计)
8. [非功能性需求](#8-非功能性需求)
9. [开发路线图](#9-开发路线图)
10. [部署与运维](#10-部署与运维)

---

## 1. 项目概述

### 1.1 愿景

求职助手是一个以 AI 驱动的个人求职自动化平台，旨在彻底消除求职过程中的繁琐手动操作。它能持续抓取职位信息、智能匹配岗位与个人简历、为每份申请自动定制简历，并实时推送通知——整个过程只需极少的日常干预。

核心理念：**自动化所有重复性工作，强化所有需要判断力的环节**。

### 1.2 问题陈述

现代求职过程令人精疲力竭：

- 每天手动查看 3–5 个招聘网站寻找相关职位
- 针对每份申请重新调整简历
- 为每个职位撰写独特的求职信
- 追踪申请状态和跟进日期
- 不知道需要提升哪些技能以改善市场竞争力

求职助手解决了上述所有问题。

### 1.3 目标用户

**主要用户**：个人求职者，尤其是：

- 在澳大利亚（墨尔本、悉尼、远程）寻找职位的软件工程师 / ML 从业者
- 进入行业的硕士 / 博士毕业生
- 正在主动转换职业方向的专业人士

**部署模式**：自托管，单用户（本地或个人云服务器）

### 1.4 核心价值主张

| 痛点                 | 解决方案                                        |
| -------------------- | ----------------------------------------------- |
| 每天查看招聘网站     | 每天上午9点自动抓取（Seek、LinkedIn Guest API） |
| 低相关度职位噪音     | AI 评分 — 只显示匹配度 ≥70% 的职位              |
| 每份申请使用通用简历 | 基于 LLM 的简历定制（针对 ATS 优化）            |
| 求职信从零开始       | 根据定制简历+职位描述自动生成                   |
| 不知道该学什么       | 仪表板技能差距分析（基于最近所有职位）          |
| 申请跟踪困难         | 集成状态追踪 + 跟进提醒                         |

---

## 2. 功能需求

### 2.1 职位发现（抓取）

| ID    | 功能                                                                   | 优先级 | 状态                                                    |
| ----- | ---------------------------------------------------------------------- | ------ | ------------------------------------------------------- |
| F-01  | Seek.com.au 抓取器（关键词+地点+日期筛选）                             | P0     | ✅ 完成                                                 |
| F-02  | Indeed.com.au 抓取器（关键词+地点+日期筛选）                           | P0     | ❌ 已移除（Cloudflare 拦截全部职位详情页，无法获取 JD） |
| F-04  | LinkedIn URL 批量解析（用户提供 URL，系统自动抓取详情）                | P1     | ❌ 已移除（`scrapers/linkedin.py` 已删除）              |
| F-04b | LinkedIn Guest API 无登录搜索（公开接口，无需账号/Cookie，无封号风险） | P1     | ✅ 完成                                                 |
| F-05  | 每次抓取可配置最大结果数                                               | P1     | ✅ 完成                                                 |
| F-06  | 基于职位 URL 去重（跳过已见职位）                                      | P0     | ✅ 完成                                                 |
| F-07  | 通过粘贴手动录入职位（Scout 页面）                                     | P1     | ✅ 完成                                                 |
| F-08  | 在可配置小时自动触发每日抓取（APScheduler）                            | P0     | ✅ 完成                                                 |

### 2.2 AI 匹配与评分（Scout Agent）

| ID    | 功能                                                                           | 优先级 | 状态    |
| ----- | ------------------------------------------------------------------------------ | ------ | ------- |
| F-10  | 解析原始职位描述 → 结构化字段（职位、公司、地点、薪资、技能）                  | P0     | ✅ 完成 |
| F-11  | ATS 关键词匹配百分比评分（integer 0–100，存为 match_score = ats_pct / 100）    | P0     | ✅ 完成 |
| F-12  | 5节结构化评估报告：匹配分析、技能提升、简历内容、格式流畅度、优先建议          | P0     | ✅ 完成 |
| F-12a | 匹配分析：ATS%进度条、强匹配项、缺失技能、未满足硬性要求、总结                 | P0     | ✅ 完成 |
| F-12b | 技能与资质改进：技术技能、证书、软技能、工具平台（各含说明）                   | P1     | ✅ 完成 |
| F-12c | 简历内容改进：要点增强建议、成就评价、量化数据建议、缺失ATS关键词              | P1     | ✅ 完成 |
| F-12d | 格式与语言改进：语气清晰度、动词替换建议、排版建议                             | P1     | ✅ 完成 |
| F-12e | 综合建议：Top 5优先行动、快速改进（1小时内）、深度改进（1–4周）、预估分数提升% | P1     | ✅ 完成 |
| F-13  | 自动过滤：丢弃 <70%，保存 70–100%                                              | P0     | ✅ 完成 |
| F-14  | 可配置评分阈值（HIGH_SCORE、MID_SCORE）                                        | P1     | ✅ 完成 |
| F-15  | 匹配度 ≥80% 时立即推送通知                                                     | P0     | ✅ 完成 |

### 2.3 简历管理

> **语言要求**：简历所有内容（摘要、工作经历、项目描述、技能列表）均以**英文**输出。Tailor Agent 的定制结果亦为英文。

| ID    | 功能                                                                            | 优先级 | 状态    |
| ----- | ------------------------------------------------------------------------------- | ------ | ------- |
| F-20  | 上传 PDF/DOCX 简历 → AI 提取结构化档案                                          | P0     | ✅ 完成 |
| F-21  | 粘贴简历文本 → AI 提取结构化档案                                                | P0     | ✅ 完成 |
| F-22  | 档案增量合并（新增+现有，不覆盖）                                               | P1     | ✅ 完成 |
| F-23  | 6 标签页档案编辑器（基本、技能、教育、经历、项目、偏好）                        | P1     | ✅ 完成 |
| F-24  | 按职位的 LLM 简历定制（关键词优化，不捏造）                                     | P0     | ✅ 完成 |
| F-24a | Tailor Agent 注入 ATS 关键词与量化建议（利用 gap_analysis.resume_improvements） | P1     | ✅ 完成 |
| F-25  | 每个定制版本的 ATS 评分                                                         | P1     | ✅ 完成 |
| F-26  | 变更摘要（修改了什么）                                                          | P1     | ✅ 完成 |
| F-27  | 来源可追溯性：每条定制要点关联原始文本                                          | P1     | ✅ 完成 |

### 2.4 求职信生成

> **语言要求**：求职信（主题行+正文）均以**英文**输出，面向澳大利亚雇主。

| ID   | 功能                                | 优先级 | 状态    |
| ---- | ----------------------------------- | ------ | ------- |
| F-30 | 根据定制简历+职位描述自动生成求职信 | P0     | ✅ 完成 |
| F-31 | 生成邮件主题行                      | P1     | ✅ 完成 |
| F-32 | 正文：3段，不超过250字，不捏造      | P0     | ✅ 完成 |
| F-33 | 生成时自动创建申请记录              | P1     | ✅ 完成 |

### 2.5 通知系统

| ID   | 功能                                           | 优先级 | 状态    |
| ---- | ---------------------------------------------- | ------ | ------- |
| F-40 | Discord 频道通知（通过 OpenClaw webhook 推送） | P0     | ✅ 完成 |
| F-41 | 高分（≥80%）职位立即推送                       | P0     | ✅ 完成 |
| F-42 | 每日摘要推送：抓取统计 + 热门职位              | P0     | ✅ 完成 |
| F-43 | 手动测试通知                                   | P1     | ✅ 完成 |
| F-44 | 通过 UI 手动触发每日 Scout                     | P1     | ✅ 完成 |

### 2.6 仪表板与分析

| ID   | 功能                                                     | 优先级 | 状态    |
| ---- | -------------------------------------------------------- | ------ | ------- |
| F-50 | 按状态统计职位数（新、已查看、已申请、面试、录用、拒绝） | P0     | ✅ 完成 |
| F-51 | 按来源统计职位数（Seek、LinkedIn、手动）                 | P1     | ✅ 完成 |
| F-52 | 评分分布统计（高分/中分数量）                            | P1     | ✅ 完成 |
| F-53 | AI 顾问报告：技能差距分析 + 市场摘要                     | P1     | ✅ 完成 |
| F-54 | 顾问 Agent 推荐行动                                      | P1     | ✅ 完成 |
| F-55 | 申请跟进提醒（逾期追踪）                                 | P1     | ✅ 完成 |
| F-56 | 申请回复率统计                                           | P2     | ✅ 完成 |

### 2.7 申请追踪

| ID   | 功能                                                  | 优先级 | 状态    |
| ---- | ----------------------------------------------------- | ------ | ------- |
| F-60 | 职位状态生命周期（新建→已查看→已申请→面试→录用/拒绝） | P0     | ✅ 完成 |
| F-61 | 申请记录（渠道：邮件/一键申请/手动）                  | P1     | ✅ 完成 |
| F-62 | 每份申请的跟进日期                                    | P1     | ✅ 完成 |
| F-63 | 申请备注                                              | P2     | ✅ 完成 |

### 2.8 设置与配置

| ID   | 功能                                     | 优先级 | 状态    |
| ---- | ---------------------------------------- | ------ | ------- |
| F-70 | 通过 UI 设置 Gemini API Key（写入 .env） | P0     | ✅ 完成 |
| F-71 | 通过 UI 配置 Discord 频道 ID             | P1     | ✅ 完成 |
| F-72 | 通过 UI 配置评分阈值                     | P1     | ✅ 完成 |
| F-73 | 通过 UI 启用/禁用调度器 + 设置运行时间   | P1     | ✅ 完成 |

---

## 3. 用户故事

### 史诗1：首次设置

**US-01** — 作为新用户，我希望上传简历 PDF，使系统自动构建我的档案，无需手动录入数据。

> 验收标准：PDF/DOCX → AI 解析 → 显示结构化档案 → 一键保存。

**US-02** — 作为新用户，我希望在 UI 中输入 Gemini API Key，使应用无需编辑配置文件即可使用。

> 验收标准：设置页面验证密钥，持久化到 .env，显示状态指示器。

### 史诗2：每日职位发现

**US-10** — 作为求职者，我希望应用每天早上自动抓取招聘网站，无需手动操作即可看到最新职位。

> 验收标准：APScheduler 在配置的时间运行；抓取 Seek、LinkedIn（Guest API）；存储结果。

**US-11** — 作为求职者，我希望收到匹配度 ≥80% 职位的即时通知，第一时间了解强匹配机会。

> 验收标准：评分后数秒内发送通知；包含职位名称、公司、评分、缺失技能。

**US-12** — 作为求职者，我希望随时手动触发特定平台的抓取，按需获取最新结果。

> 验收标准：抓取器页面提供各平台"立即运行"按钮；显示进度和结果。

**US-13** — 作为求职者，我希望粘贴任意来源的职位描述，分析抓取器未覆盖的职位。

> 验收标准：Scout 页面接受原始职位描述；10秒内返回匹配评分+差距分析。

### 史诗3：查看与申请

**US-20** — 作为求职者，我希望看到按排名排列的匹配职位列表，优先处理最相关的机会。

> 验收标准：职位页面按匹配评分排序；可按状态筛选和搜索。

**US-21** — 作为求职者，我希望为特定职位生成定制简历，在不花费30分钟的情况下最大化 ATS 通过率。

> 验收标准：一键定制；显示 ATS 评分、修改内容及每条要点的来源文本。

**US-22** — 作为求职者，我希望从定制简历自动生成求职信，几秒内获得有力的起点。

> 验收标准：求职信显示主题行+3段正文；自动创建申请记录。

**US-23** — 作为求职者，我希望更新职位状态（已查看、已申请、拒绝），追踪每份申请进度。

> 验收标准：职位详情中有状态下拉框；状态标签在列表视图中立即更新。

### 史诗4：进度追踪

**US-30** — 作为求职者，我希望看到求职仪表板摘要，一眼了解已申请数量和流水线状态。

> 验收标准：仪表板显示按状态统计、回复率、来源分布。

**US-31** — 作为求职者，我希望看到错过职位中出现最频繁的技能，了解下一步该学什么。

> 验收标准：顾问板块显示前5个缺失技能及出现频次+推荐行动。

**US-32** — 作为求职者，我希望收到需要跟进申请的提醒，不让好机会就此冷却。

> 验收标准：仪表板跟进表格显示 follow_up_date ≤ 今天的申请。

### 史诗5：档案管理

**US-40** — 作为求职者，我希望手动编辑技能和经历，使档案在解析简历后保持准确。

> 验收标准：6标签页档案编辑器，每个板块支持增删改；修改立即持久化。

**US-41** — 作为求职者，我希望将新版简历与现有档案合并，不丢失手动添加的信息。

> 验收标准：解析新简历 → 并排预览 → 合并只增量更新现有档案。

---

## 4. 技术架构

### 4.1 系统概览

```
┌─────────────────────────────────────────────────────────┐
│                     用户浏览器                            │
│              React 18 + TypeScript + Tailwind            │
│                  (localhost:5173 / Vite)                 │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/JSON (Axios)
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI 后端                             │
│               (localhost:8000 / Uvicorn)                 │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  路由层   │  │  Agent   │  │  抓取器   │  │ 调度器 │  │
│  │ (REST API│  │ (AI逻辑) │  │(Playwright│  │(APSched│  │
│  │  层)     │  │          │  │  + HTTP) │  │  uler) │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       └─────────────┴─────────────┴─────────────┘       │
│                    SQLite (SQLModel ORM)                  │
│                 data/db/jobseeking.db                    │
└──────────────────────────┬──────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
   │  Gemini API  │  │  招聘网站   │  │  Discord   │
   │(google-genai)│  │Seek/Indeed  │  │  Webhook   │
   │              │  │ /LinkedIn  │  │            │
   └──────────────┘  └─────────────┘  └────────────┘
```

### 4.2 技术栈

| 层级        | 技术                    | 版本   | 选型理由                    |
| ----------- | ----------------------- | ------ | --------------------------- |
| 前端框架    | React                   | 18.3   | 生态系统完善，SPA 能力强    |
| 前端构建    | Vite                    | 5.3    | 快速 HMR 开发体验           |
| 前端样式    | Tailwind CSS            | 3.4    | 实用优先，快速构建 UI       |
| 前端 HTTP   | Axios                   | 1.7    | 基于 Promise，支持拦截器    |
| 前端路由    | React Router            | 6.23   | 文件路由                    |
| 后端框架    | FastAPI                 | 0.134  | 异步，自动生成 OpenAPI 文档 |
| 后端服务器  | Uvicorn                 | 0.41   | ASGI，生产就绪              |
| ORM         | SQLModel                | 0.0.22 | SQLAlchemy + Pydantic 混合  |
| 数据库      | SQLite                  | —      | 零配置，可移植              |
| AI 提供商   | Google Gemini 2.5 Flash | —      | 结构化输出，响应快          |
| 网页抓取    | Playwright              | 1.40   | 无头 Chromium，抗反爬机制   |
| 调度器      | APScheduler             | 3.10   | 进程内类 Cron 调度          |
| PDF 解析    | pypdf                   | 4.0    | 纯 Python，无原生依赖       |
| DOCX 解析   | python-docx             | 1.1    | 纯 Python                   |
| HTTP 客户端 | httpx                   | 0.27   | 异步，用于 Webhook          |
| 时区        | pytz                    | 2024   | 调度器使用 AEDT 时区        |

### 4.3 模块职责

```
backend/app/
├── main.py            — 应用工厂、CORS、路由注册、生命周期钩子
├── config.py          — 所有环境变量+路径的单一来源
├── database.py        — SQLite 引擎初始化、数据表创建、会话工厂
├── scheduler.py       — APScheduler 设置，每日任务触发
├── notifications.py   — Webhook 推送函数（高分、每日摘要）
│
├── agents/
│   ├── parser.py      — 简历文本 → UserProfile（Gemini 结构化输出）
│   ├── scout.py       — 职位描述 → 解析字段 + 匹配评分 + 差距分析
│   ├── tailor.py      — 档案 + 职位描述 → 定制简历版本
│   └── cover_letter.py — 档案 + 定制简历 + 职位描述 → 求职信
│
├── scrapers/
│   ├── seek.py            — Seek.com.au Playwright 抓取器
│   ├── linkedin_guest.py    — LinkedIn Guest API 无登录抓取器（httpx + BeautifulSoup，调用 /jobs-guest 公开接口）
│   └── scheduler.py       — 编排器：运行所有抓取器 → 评分 → 通知
│
├── models/
│   ├── job.py         — Job SQLModel 数据表
│   ├── application.py — Application SQLModel 数据表
│   ├── resume_version.py — ResumeVersion SQLModel 数据表
│   └── user_profile.py   — UserProfile Pydantic 模型（JSON 文件）
│
└── routers/
    ├── jobs.py         — /api/jobs/* 端点
    ├── profile.py      — /api/profile/* 端点
    ├── scrapers.py     — /api/scrapers/* + 后台任务轮询
    ├── notifications.py — /api/notifications/* 端点
    ├── settings.py     — /api/settings/* 端点
    └── dashboard.py    — /api/dashboard/* 端点
```

### 4.4 AI 集成模式

所有 AI 调用均使用 **Gemini 2.5 Flash**，通过 `google-genai` SDK 以**结构化输出**（JSON Schema 强制执行）：

```
用户数据 / 原始职位描述
       │
       ▼
  Gemini API（结构化输出 Schema）
       │
       ▼
  经过验证的 Pydantic 模型
       │
       ▼
  保存到数据库 / 返回给客户端
```

Agent 不会捏造输入之外的数据。Tailor Agent 通过提示约束和 source_raw 可追溯性强制执行此规则。

> **语言约束**：Tailor Agent 和 Cover Letter Agent 的所有输出强制为英文，与目标市场（澳大利亚）保持一致。Parser Agent 解析用户上传的简历时兼容中英文输入，但结构化存储后的内容统一以英文表示。

### 4.5 LinkedIn 抓取策略说明

LinkedIn 对自动化搜索行为有严格的封号机制，因此系统采用以下策略：

| 方式                          | 封号风险 | 说明                                                                                                |
| ----------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| 自动登录搜索（已移除）        | ⚠️ 高    | 频繁搜索+翻页触发行为检测，不采用                                                                   |
| Cookie 文件登录（已移除）     | ⚠️ 高    | 账号风险，不采用                                                                                    |
| URL 批量解析（已移除，F-04）  | 🟡 中    | 已删除 `scrapers/linkedin.py`                                                                       |
| Guest API 无登录搜索（F-04b） | 🟢 低    | 调用 LinkedIn 对未登录用户/搜索引擎开放的公开接口（`/jobs-guest/jobs/api/`），无需任何账号或 Cookie |

**实现原理**：`scrapers/linkedin_guest.py` 分两步：

1. 调用 `/jobs-guest/jobs/api/seeMoreJobPostings/search` 获取职位卡片列表（与普通游客访问搜索页相同）
2. 对每个职位调用 `/jobs-guest/jobs/api/jobPosting/{job_id}` 获取完整 JD 正文

**当前主力来源**：Seek（Playwright）+ LinkedIn Guest API（httpx）。Indeed 因 Cloudflare 防护无法抓取职位详情，已移除。

### 4.6 后台任务模式

长时间运行的操作（抓取、评分）使用 FastAPI `BackgroundTasks` 配合内存任务注册表：

```
POST /api/scrapers/seek
  → 创建 task_id（UUID）
  → 启动 BackgroundTask
  → 返回 { task_id }

GET /api/tasks/{task_id}
  → 返回 { status, progress, results, error }
  → 客户端轮询直到 status == "done" | "error"
```

---

## 5. 数据模型

### 5.1 Job（SQLite 数据表）

```python
class Job(SQLModel, table=True):
    id: str                     # UUID，主键
    source: str                 # "seek" | "linkedin" | "manual"
    raw_jd: str                 # 完整原始职位描述文本
    title: str                  # 解析后的职位名称
    company: str                # 公司名称
    location: str               # 职位地点
    salary_range: str           # 薪资范围（原始字符串，可能为空）
    skills_required: list[str]  # 职位描述中所需技能的 JSON 列表
    match_score: float          # 0.0–1.0（= ats_pct / 100，来自 EVAL_SCHEMA）
    gap_analysis: dict          # 完整5节评估报告（见下方 Schema）
    source_url: str             # 原始职位发布 URL
    status: JobStatus           # 枚举（见下方）
    notification_sent: bool     # 是否已发送推送通知
    created_at: datetime
    updated_at: datetime
```

**gap_analysis Schema**（v2.2 扩展，向后兼容旧记录）：

```json
{
  "ats_pct": 75,
  "strong_matches": ["3年Python经验", "React+TypeScript项目"],
  "missing_skills": ["AWS认证", "5年以上Java经验"],
  "unmet_requirements": ["要求CS学位"],
  "notes": "总体适配良好，需补充云平台经验。",
  "skills_improvements": {
    "technical": ["学习 AWS SageMaker，因该职位强调云端ML部署"],
    "certifications": ["AWS Certified ML Specialty"],
    "soft_skills": ["展示跨团队协作经验"],
    "tools": ["dbt", "Airflow", "Terraform"]
  },
  "resume_improvements": {
    "bullet_strength": ["为ML流水线要点添加量化结果"],
    "achievements_feedback": "简历侧重职责描述，建议增加更多成果导向表述。",
    "metrics_suggestions": ["量化API服务的用户规模"],
    "ats_keywords": ["MLOps", "Feature Store", "Model Registry"]
  },
  "formatting_improvements": {
    "tone_clarity": ["部分句子过长，建议拆分"],
    "action_verbs": ["将 'helped with' 替换为 'Led'"],
    "layout": ["技能部分建议置于经历之前"]
  },
  "recommendations": {
    "top_5": ["在技能区加入'Agile'关键词", "..."],
    "quick_wins": ["添加缺失ATS关键词到技能列表（30分钟内）"],
    "deeper_improvements": ["完成AWS ML证书（约4周）"],
    "estimated_improvement_pct": 15
  }
}
```

**JobStatus 枚举**：

```
新建 → 已查看 → 已申请 → 面试 → 录用
                        ↘ 拒绝
              ↘ 忽略
```

### 5.2 Application（SQLite 数据表）

```python
class Application(SQLModel, table=True):
    id: str                         # UUID
    job_id: str                     # 外键 → Job.id
    resume_version_id: str | None   # 外键 → ResumeVersion.id
    channel: ApplicationChannel     # "email" | "easy_apply" | "manual"
    applied_at: datetime
    follow_up_date: date | None     # 何时跟进
    notes: str                      # 自由文本备注
    status: str                     # "pending" | "responded" | "rejected" 等
```

### 5.3 ResumeVersion（SQLite 数据表）

```python
class ResumeVersion(SQLModel, table=True):
    id: str             # UUID
    job_id: str         # 外键 → Job.id
    content_json: dict  # 完整定制简历内容（见下方）
    ats_score: float    # 所需技能覆盖率（%）
    changes_summary: str # 人类可读的差异摘要
    created_at: datetime
```

**content_json Schema**：

```json
{
  "summary": "针对职位定制的2-3句专业摘要",
  "selected_skills": ["技能1", "技能2"],
  "tailored_experience": [
    {
      "company": "...",
      "role": "...",
      "duration": "...",
      "bullets": [
        {
          "raw": "重写后的要点文本",
          "source_raw": "档案中的原始文本",
          "tech": ["技术1", "技术2"],
          "metric": "量化结果"
        }
      ]
    }
  ],
  "tailored_projects": [...],
  "changes_summary": "重新排列了技能，突出了 X、Y 关键词..."
}
```

### 5.4 UserProfile（JSON 文件 — `data/user_profile.json`）

```python
class UserProfile(BaseModel):
    name: str
    target_roles: list[str]
    skills: list[Skill]           # {name, level, years}
    experience: list[Experience]  # {company, role, duration, bullets}
    projects: list[Project]       # {name, description, tech_stack, bullets}
    education: list[Education]    # {institution, degree, field, duration, gpa}
    preferences: Preferences      # {locations, salary_range, job_types}
```

> **设计决策**：UserProfile 存储为 JSON 文件（而非 SQLite），原因：单用户系统只有一份档案；频繁整体读取-修改-写入；更易于检查和版本控制。

### 5.5 ScrapedJob（内存数据类）

```python
@dataclass
class ScrapedJob:
    url: str
    raw_jd: str
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
```

用作抓取器输出和 Scout Agent 输入之间的中间表示。不持久化——评分后丢弃。

---

## 6. API 设计

### 6.1 基本约定

- **开发基础 URL**：`http://localhost:8000`
- **所有 API 路由**：前缀为 `/api/`
- **认证**：无（单用户，信任本地主机模式）
- **请求格式**：`application/json`（文件端点：`multipart/form-data`）
- **错误格式**：`{ "detail": "错误信息" }`

### 6.2 职位 API

#### `GET /api/jobs`

列出所有职位，支持可选筛选。

**查询参数**：

| 参数        | 类型   | 默认值 | 说明              |
| ----------- | ------ | ------ | ----------------- |
| `status`    | string | —      | 按 JobStatus 筛选 |
| `min_score` | float  | —      | 最低匹配评分      |

---

#### `POST /api/jobs/scout`

手动分析职位描述。

**请求体**：

```json
{
  "raw_jd": "完整职位描述文本...",
  "source": "manual",
  "auto_filter": false
}
```

---

#### `PUT /api/jobs/{job_id}/status`

更新职位状态。

**请求体**：`{ "status": "reviewed" }`

---

#### `POST /api/jobs/{job_id}/tailor`

为特定职位生成定制简历版本。

**响应**：

```json
{
  "resume_version": { ...ResumeVersion },
  "ats_score": 0.87,
  "changes_summary": "..."
}
```

---

#### `POST /api/jobs/{job_id}/cover-letter`

生成求职信并记录申请。

**响应**：

```json
{
  "subject_line": "申请高级 ML 工程师职位 — 您的姓名",
  "body": "尊敬的招聘经理，\n\n...",
  "application_id": "uuid"
}
```

### 6.3 档案 API

| 方法 | 路径                         | 说明               |
| ---- | ---------------------------- | ------------------ |
| GET  | `/api/profile`               | 获取当前用户档案   |
| PUT  | `/api/profile`               | 保存完整用户档案   |
| POST | `/api/profile/upload-resume` | 上传简历文件并解析 |
| POST | `/api/profile/parse-resume`  | 解析粘贴的简历文本 |

### 6.4 抓取器 API

| 方法   | 路径                     | 说明                                                    |
| ------ | ------------------------ | ------------------------------------------------------- |
| POST   | `/api/scrapers/seek`     | 启动 Seek 后台抓取任务（Playwright）                    |
| POST   | `/api/scrapers/linkedin` | 启动 LinkedIn Guest API 后台抓取任务（httpx，无需账号） |
| GET    | `/api/tasks/{task_id}`   | 轮询后台任务状态                                        |
| DELETE | `/api/tasks/{task_id}`   | 取消进行中的后台任务                                    |

**任务状态响应**：

```json
{
  "status": "running",
  "progress": "已抓取 8/15 个职位...",
  "results": [...],
  "error": null
}
```

### 6.5 仪表板 API

#### `GET /api/dashboard/stats`

**响应**：

```json
{
  "total": 142,
  "by_status": { "new": 45, "reviewed": 30, "applied": 20 },
  "by_source": { "seek": 60, "linkedin": 38, "manual": 4 },
  "high_score_count": 18,
  "mid_score_count": 62
}
```

#### `GET /api/dashboard/advisor`

AI 顾问报告——技能差距分析。

**响应**：

```json
{
  "top_missing_skills": [
    { "skill": "Kubernetes", "count": 32 },
    { "skill": "dbt", "count": 18 }
  ],
  "recommended_actions": ["学习 Kubernetes", "在作品集中添加 dbt 项目"]
}
```

### 6.6 设置 API

#### `GET /api/settings`

**响应**：

```json
{
  "gemini_api_key_set": true,
  "high_score_threshold": 0.8,
  "mid_score_threshold": 0.7,
  "scheduler_enabled": true,
  "scheduler_hour": 9
}
```

---

## 7. UI/UX 设计

### 7.1 布局

单页面应用，左侧持久导航栏（240px）：

```
┌──────────┬────────────────────────────────────────┐
│          │                                        │
│  侧边栏  │           主要内容区域                   │
│  (240px) │         （可滚动，全高）                 │
│          │                                        │
│ ● 仪表板 │                                        │
│ ● 职位   │                                        │
│ ● 抓取器 │                                        │
│ ● 通知   │                                        │
│ ● 档案   │                                        │
│ ● 简历   │                                        │
│ ● 设置   │                                        │
└──────────┴────────────────────────────────────────┘
```

**侧边栏**：深色（gray-900），白色文字，当前页面高亮显示

### 7.2 设计规范

| 设计变量   | 值                 |
| ---------- | ------------------ |
| 主色调     | Indigo-600         |
| 侧边栏背景 | Gray-900           |
| 卡片背景   | White              |
| 边框颜色   | Gray-200           |
| 高分颜色   | Green-600          |
| 中分颜色   | Yellow-600         |
| 低分颜色   | Red-600            |
| 状态标签   | 按状态色彩编码     |
| 字体       | 系统默认（无衬线） |

### 7.3 响应式策略

当前实现面向桌面端（1280px+）。v2.0 未实现移动端响应式布局，计划在 v2.1 更新中实现侧边栏折叠为图标的窄视口方案。

---

## 8. 非功能性需求

### 8.1 性能

| 指标                        | 目标             | 备注                            |
| --------------------------- | ---------------- | ------------------------------- |
| AI Agent 响应（Scout 评估） | < 20秒/职位      | 5节结构化输出，输出量大于原评分 |
| AI Agent 响应（定制）       | < 15秒           | 处理较长上下文                  |
| 抓取吞吐量                  | 约2-3个职位/分钟 | 含反爬延迟                      |
| 每日全量 Scout（50个职位）  | < 10分钟         | 后台运行可接受                  |
| API 响应（非 AI）           | < 500毫秒        | 仅数据库查询                    |
| 前端首次加载                | < 3秒            | Vite 打包优化                   |

### 8.2 可靠性

- **无需认证**：单用户信任模型，无需登录会话管理
- **优雅降级**：LinkedIn URL 解析失败时 → 跳过 LinkedIn，继续 Seek/Indeed
- **幂等抓取**：基于 URL 去重，防止重复处理
- **错误隔离**：每个抓取器独立运行，一个失败不影响其他

### 8.3 安全性

| 安全关注点   | 缓解措施                                        |
| ------------ | ----------------------------------------------- |
| API Key 存储 | 写入 `.env` 文件（不提交到 git）                |
| CORS         | 开发环境限制为 localhost:5173 和 localhost:8000 |
| 文件上传     | 仅接受 PDF/DOCX/TXT                             |
| SQL 注入     | SQLModel ORM 参数化查询；无原始 SQL             |
| Prompt 注入  | LLM 输入为结构化（仅职位描述文本）              |
| 无认证       | 适用于本地/受信任部署；**不适合多用户公开托管** |

### 8.4 可扩展性

**当前范围**：单用户，本地部署。未设计为多租户。

潜在扩展路径（v3.0+）：

- 添加用户认证（JWT）
- 迁移至 PostgreSQL
- 使用 Docker Compose 容器化
- 添加任务队列（Celery + Redis）

### 8.5 可测试性

- 后端测试套件：`backend/tests/` — **120 个测试，全部通过**
- 测试命令：`PYTHONPATH=. python3 -m pytest backend/tests/ -v`
- 覆盖范围：Agent、抓取器、路由、数据模型
- 前端：v2.0 无自动化测试（手动测试）

### 8.6 ATS 评分说明（重要限制）

`match_score`（= `ats_pct / 100`）是由 **Gemini LLM 估算**的关键词匹配百分比，**不是**真实 ATS 系统的解析结果。

已知局限性：
- LLM 倾向于给出偏高分数（flattery bias）
- 真实 ATS 系统的解析逻辑（字体、格式、关键词位置权重）无法模拟
- 分数仅供**排序参考**，不代表实际投递通过率

UI 显示要求：所有展示 `match_score` 的界面必须附带说明文字"AI 估算，仅供参考"。

---

## 9. 开发路线图

### v2.0 ✅

- 完整自动抓取流水线（Seek、Indeed、LinkedIn）
- AI Scout Agent（匹配评分 + 自动过滤）
- 简历解析与定制
- 求职信生成
- 通知系统（Discord，通过 OpenClaw webhook）
- APScheduler 每日自动化
- React 仪表板（共8个页面）
- 106 个通过测试

### v2.1 ✅

| 功能                          | 优先级 | 状态    | 备注                                                                                                     |
| ----------------------------- | ------ | ------- | -------------------------------------------------------------------------------------------------------- |
| 简历 PDF 导出                 | P1     | ✅ 完成 | WeasyPrint + Jinja2，`templates/resume.html`                                                             |
| 前端 PDF 下载按钮             | P1     | ✅ 完成 | Jobs 页面"Download PDF"按钮                                                                              |
| LinkedIn Guest API 无登录抓取 | P1     | ✅ 完成 | `scrapers/linkedin_guest.py` + `/api/scrapers/linkedin`；调用 LinkedIn 公开 `/jobs-guest` 接口，无需账号 |

### v2.2 — 当前版本 ✅

| 功能                           | 优先级 | 状态      | 备注                                                         |
| ------------------------------ | ------ | --------- | ------------------------------------------------------------ |
| Scout Agent 5节结构化评估报告  | P1     | ✅ 完成   | `EVAL_SYSTEM` + `EVAL_SCHEMA`，替代原 `SCORE_SYSTEM`         |
| ATS匹配百分比评分（`ats_pct`） | P1     | ✅ 完成   | 取代原 `match_score` 直接输出，`match_score = ats_pct / 100` |
| `EvaluationReport` 共享组件    | P1     | ✅ 完成   | `frontend/src/components/EvaluationReport.tsx`               |
| Scout 页面 5节折叠评估展示     | P1     | ✅ 完成   | 替代原2列强匹配/缺失技能                                     |
| Jobs 页面"查看完整评估"展开区  | P1     | ✅ 完成   | 保留摘要 + 可展开全评估                                      |
| 移动端响应式 UI                | P1     | 🔲 待开发 | 可折叠侧边栏，触控友好                                       |
| 职位备注/标签                  | P2     | 🔲 待开发 | 用户自定义标签                                               |
| 多简历档案                     | P2     | 🔲 待开发 | 针对不同职位类型使用不同档案                                 |
| Seek 自动申请                  | P2     | 🔲 待开发 | 通过 Playwright 自动化一键 Easy Apply                        |
| Indeed 自动申请                | P2     | 🔲 待开发 | 表单填写自动化                                               |

### v2.3 — 当前版本 ✅

| 功能                        | 优先级 | 状态    | 备注                                                                                                                                                                                                          |
| --------------------------- | ------ | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tailor Agent ATS 关键词注入 | P1     | ✅ 完成 | 松绑 STRICT RULE 1：允许织入 JD 术语；新增 Rule 6；Prompt 增加 `## Target ATS Keywords` 和 `## Quantification Opportunities` 两节，数据来自 `gap_analysis.resume_improvements`（Scout 已产出，v2.3 前未使用） |

### v2.3 — 工程质量修复（`fix/engineering-quality`）

| Task | 内容 | 优先级 | 状态 |
| ---- | ---- | ------ | ---- |
| EQ-01 | `notifications.py` 新增模块级常量 `NOTIFICATION_WEBHOOK_URL` / `NOTIFICATION_CHAT_ID`，`_send()` 使用模块级变量而非每次读 `os.environ` | P0 | ✅ 完成 |
| EQ-02 | `backend/tests/conftest.py` 新增 `mock_load_dotenv` fixture，防止 `config.py` reload 时重读 `.env` 干扰测试 | P0 | ✅ 完成 |
| EQ-03 | `models/job.py` + `routers/dashboard.py`：`datetime.utcnow()` → `datetime.now(timezone.utc)` | P1 | ✅ 完成 |
| EQ-04 | `scrapers/seek.py`：`print()` → `logger.warning()` | P1 | ✅ 完成 |
| EQ-05 | `scrapers/scheduler.py`：Seek 抓取遍历所有 locations，而非仅 `locations[0]` | P1 | ✅ 完成 |
| EQ-06 | `src/` 目录新增 `DEPRECATED.md`，标注已被 `backend/` 取代 | P1 | ✅ 完成 |
| EQ-07 | 前端 ATS 评分展示处加"AI 估算，仅供参考"说明（对应 8.6 节要求） | P1 | ✅ 完成 |

**验收标准**：`PYTHONPATH=. python3 -m pytest backend/tests/ -v` 全部通过，无 `DeprecationWarning`。

### v2.3 — 中期规划

| 功能             | 优先级 | 备注                                   |
| ---------------- | ------ | -------------------------------------- |
| PDF 生成引擎改用 Playwright | P2 | 修复现有导出格式变形问题：`weasyprint`/`jinja2` 从未声明进 `requirements.txt`/`uv.lock`；WeasyPrint 是自实现的 CSS 引擎，flexbox/中文字体回退支持不完整（模板当前用 `font-family: Arial`，无中文字形）。方案：复用项目已有的 `playwright` 依赖（Seek 爬虫已用），`page.pdf(format="A4", print_background=True)` 直接渲染 `templates/resume.html`，与真实浏览器预览一致，不会有引擎间不一致导致的变形。范围仅限修复现有单模板渲染质量，**不做 FlowCV 式的多模板/用户自定义模板**；DOCX 导出本次不动。需同步更新附录 C（当前记录的是 WeasyPrint 方案）及 `pdf_generator.py`。非紧急，暂缓 |
| 求职数据分析仪表盘（Analytics + DW + Tableau） | P2 | 面向求职（Data Engineer 方向）作品集展示。项目内新增 raw SQL 分析页 + Snowflake 星型模型 + Tableau Public 公开仪表盘。详细方案见**附录 E**。非紧急，暂缓 |
| 邮件集成         | P2     | 通过 SMTP 从应用直接发送求职信         |
| 面试准备         | P3     | LLM 生成职位专属面试问题+答案          |
| 公司调研         | P3     | 自动从 LinkedIn/Glassdoor 获取公司信息 |
| 申请日历         | P2     | 申请和跟进的可视化时间轴               |
| 导出 CSV/PDF     | P2     | 导出职位列表和统计数据                 |
| Glassdoor 抓取器 | P3     | 额外职位来源                           |

### v3.0 — 长期愿景

| 功能        | 备注                                     |
| ----------- | ---------------------------------------- |
| 多用户支持  | 认证（JWT）、PostgreSQL、用户隔离        |
| 浏览器扩展  | 一键从任意招聘网站快速添加职位           |
| 作品集集成  | 自动将 GitHub 项目关联到技能和经历       |
| 薪资基准    | 从抓取数据对比目标薪资与市场水平         |
| AI 面试教练 | 模拟面试问答与反馈                       |
| 云端托管    | Docker Compose + Render/Railway 一键部署 |

---

## 10. 部署与运维

### 10.1 本地开发

**前置条件**：Python 3.12+、Node.js 20+、Gemini API Key

**后端启动**：

```bash
cd /home/zhang/projects/Jobseeking_Agent
pip install -r backend/requirements.txt
playwright install chromium

# 创建 .env
echo "GEMINI_API_KEY=your_key_here" > .env
echo "SCHEDULER_ENABLED=true" >> .env

# 启动后端
uvicorn backend.app.main:app --reload
# → http://localhost:8000
# → 文档：http://localhost:8000/docs
```

**前端启动**：

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

**运行测试**：

```bash
PYTHONPATH=. python3 -m pytest backend/tests/ -v
```

### 10.2 环境变量

| 变量名                 | 是否必需 | 默认值  | 说明                         |
| ---------------------- | -------- | ------- | ---------------------------- |
| `GEMINI_API_KEY`       | ✅ 必需  | —       | Google Gemini API Key        |
| `DISCORD_CHANNEL_ID`   | 否       | —       | Discord 推送频道 ID          |
| `HIGH_SCORE_THRESHOLD` | 否       | `0.80`  | 即时推送的评分阈值           |
| `MID_SCORE_THRESHOLD`  | 否       | `0.70`  | 保存职位的最低阈值           |
| `SCHEDULER_ENABLED`    | 否       | `false` | 启用每日自动抓取             |
| `SCHEDULER_HOUR`       | 否       | `9`     | 运行小时（AEDT 时间）        |
| `DEFAULT_MAX_JOBS`     | 否       | `15`    | 每次抓取查询的默认最大职位数 |

### 10.3 文件系统布局

```
data/
├── db/
│   └── jobseeking.db          # SQLite 数据库（自动创建）
├── resumes/
│   └── *.pdf / *.docx         # 上传的简历文件
├── cover_letters/
│   └── cover_letter_*.txt     # 生成的求职信
├── user_profile.json          # 当前用户档案
└── user_profile.example.json  # 模板/参考
```

### 10.4 Docker 部署

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    environment:
      - VITE_API_URL=http://backend:8000
```

```bash
docker-compose up -d
```

### 10.5 LinkedIn 职位抓取方式

系统通过 LinkedIn Guest API 自动抓取职位，无需任何账号或 Cookie（F-04b，✅ 已实现）：

**流程（`POST /api/scrapers/linkedin`）**：

1. 在抓取器页面配置关键词（如 `ML Engineer`）和地点（如 `Sydney, Australia`）
2. 系统调用 LinkedIn 对未登录用户开放的公开搜索接口，获取职位列表
3. 对每个职位调用公开职位详情接口获取完整 JD
4. 自动评分、过滤、保存，无需任何登录凭据

> **注**：F-04（URL 批量解析）和 F-02（Indeed 抓取）均已移除。

### 10.6 监控与可观测性

**当前状态**：所有日志通过 Python `logging` 模块输出到 stdout。

**日志级别**：

- `INFO`：抓取器进度、职位已保存、通知已发送
- `WARNING`：抓取器返回0条结果、LinkedIn URL 无法访问
- `ERROR`：API 失败、数据库错误、Agent 异常

**v2.1 建议新增**：

- 结构化 JSON 日志
- 日志文件轮转
- 简单健康检查端点（`GET /health`）

---

## 附录 C：定制简历 PDF 生成方案

### C.1 背景与问题

Tailor Agent 生成定制内容后，需要输出一份可直接投递的 PDF 简历。由于用户简历模板来自 FlowCV（app.flowcv.com）导出的**纯排版 PDF**（无表单字段，文本嵌入固定坐标），直接在 PDF 上做文字替换会导致字体不匹配，视觉质量不可接受。

### C.2 方案选型

| 方案                  | 字体匹配    | 实现难度 | 推荐度     |
| --------------------- | ----------- | -------- | ---------- |
| pymupdf 直接覆盖替换  | ❌ 字体会变 | 低       | 不推荐     |
| WeasyPrint HTML → PDF | ✅ 完全可控 | 中       | ⭐⭐⭐⭐   |
| reportlab 从零绘制    | ✅ 完全可控 | 高       | ⭐⭐⭐     |
| FlowCV API（若开放）  | ✅ 原生样式 | 低       | ⭐⭐⭐⭐⭐ |

**选定方案：WeasyPrint HTML → PDF**

核心思路：将 FlowCV 模板在浏览器中另存为 HTML，清理后作为 Jinja2 模板，由 Tailor Agent 输出的结构化数据填充，最终通过 WeasyPrint 渲染为 PDF。样式几乎无需重写，直接复用 FlowCV 的 CSS。

### C.3 技术架构

```
FlowCV 导出 PDF
    │
    ▼（浏览器另存为 HTML，一次性操作）
Jinja2 模板（resume.html）
    │
    ├── Tailor Agent 输出（content_json）
    │       ↓
    │   Jinja2 渲染
    │       ↓
    └── WeasyPrint → tailored_{job_id}.pdf
```

### C.4 实现细节

#### 依赖安装

```bash
pip install weasyprint jinja2
```

#### HTML 模板结构（`templates/resume.html`）

```html
<style>
  body {
    font-family: "Calibri", sans-serif;
    margin: 40px;
    color: #333;
  }
  h1 {
    font-size: 24px;
    font-weight: bold;
  }
  h2 {
    font-size: 14px;
    border-bottom: 1px solid #ccc;
    color: #2e75b6;
    margin-top: 16px;
  }
  p {
    font-size: 11px;
    margin: 4px 0;
  }
  ul {
    font-size: 11px;
    margin: 4px 0 8px 16px;
  }
  .skill-tag {
    display: inline-block;
    background: #f0f0f0;
    padding: 2px 8px;
    margin: 2px;
    border-radius: 3px;
    font-size: 10px;
  }
</style>

<h1>{{ name }}</h1>
<p>{{ email }} | {{ phone }} | {{ location }}</p>

<h2>SUMMARY</h2>
<p>{{ summary }}</p>

<h2>SKILLS</h2>
{% for skill in selected_skills %}
<span class="skill-tag">{{ skill }}</span>
{% endfor %}

<h2>EXPERIENCE</h2>
{% for exp in tailored_experience %}
<p><strong>{{ exp.role }}</strong> — {{ exp.company }} ({{ exp.duration }})</p>
<ul>
  {% for bullet in exp.bullets %}
  <li>{{ bullet.raw }}</li>
  {% endfor %}
</ul>
{% endfor %}

<h2>PROJECTS</h2>
{% for proj in tailored_projects %}
<p><strong>{{ proj.name }}</strong> | {{ proj.tech_stack | join(', ') }}</p>
<ul>
  {% for bullet in proj.bullets %}
  <li>{{ bullet }}</li>
  {% endfor %}
</ul>
{% endfor %}

<h2>EDUCATION</h2>
{% for edu in education %}
<p>
  <strong>{{ edu.degree }}</strong> — {{ edu.institution }} ({{ edu.duration }})
</p>
{% endfor %}
```

#### PDF 生成函数（`app/pdf_generator.py`）

```python
from weasyprint import HTML
from jinja2 import Template
import os

def generate_resume_pdf(
    tailored_content: dict,
    profile: dict,
    template_path: str,
    output_path: str
) -> str:
    with open(template_path) as f:
        tmpl = Template(f.read())

    # 合并档案基本信息 + Tailor Agent 输出
    render_data = {
        "name": profile.get("name", ""),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "location": profile.get("location", ""),
        "education": profile.get("education", []),
        **tailored_content   # summary, selected_skills, tailored_experience, tailored_projects
    }

    html_content = tmpl.render(**render_data)
    HTML(string=html_content).write_pdf(output_path)
    return output_path
```

#### 集成到 Tailor 路由（`routers/jobs.py`）

```python
from app.pdf_generator import generate_resume_pdf

@router.post("/{job_id}/tailor")
async def tailor_resume(job_id: str, db: Session = Depends(get_session)):
    job = db.get(Job, job_id)
    profile = load_user_profile()

    # 现有逻辑：Tailor Agent 生成定制内容
    resume_version = await tailor_agent.run(job, profile)

    # 新增：自动生成定制 PDF
    pdf_path = f"data/resumes/tailored_{job_id}.pdf"
    generate_resume_pdf(
        tailored_content=resume_version.content_json,
        profile=profile.dict(),
        template_path="templates/resume.html",
        output_path=pdf_path
    )

    return {
        "resume_version": resume_version,
        "pdf_download_url": f"/api/files/{job_id}/resume.pdf"
    }
```

#### 文件下载端点（`routers/files.py`）

```python
from fastapi.responses import FileResponse

@router.get("/{job_id}/resume.pdf")
def download_resume(job_id: str):
    path = f"data/resumes/tailored_{job_id}.pdf"
    return FileResponse(path, media_type="application/pdf",
                        filename=f"resume_{job_id}.pdf")
```

### C.5 文件系统新增路径

```
data/
├── resumes/
│   ├── tailored_{job_id}.pdf    # 每个职位的定制 PDF 简历（新增）
│   └── *.pdf / *.docx           # 上传的原始简历文件
templates/
└── resume.html                   # Jinja2 简历模板（新增）
```

### C.6 功能需求补充

| ID   | 功能                                        | 优先级 | 状态    |
| ---- | ------------------------------------------- | ------ | ------- |
| F-28 | 基于 Tailor Agent 输出自动生成定制 PDF 简历 | P1     | ✅ 完成 |
| F-29 | 通过 UI 下载定制 PDF 简历                   | P1     | ✅ 完成 |

### C.7 注意事项

- **中文支持**：WeasyPrint 默认不包含中文字体，若简历包含中文内容需在 CSS 中指定系统字体路径，或使用 `@font-face` 嵌入字体文件
- **样式还原**：首次使用时需人工对比 FlowCV 导出效果，微调 HTML 模板的字号、间距、颜色
- **多模板支持**：未来可扩展为多套模板，在 `preferences` 中配置默认模板

---

## 附录 A：Gemini Agent 提示 Schema

### Scout Agent — 解析 Schema

```json
{
  "title": "string",
  "company": "string",
  "location": "string",
  "salary_range": "string",
  "skills_required": ["string"]
}
```

### Scout Agent — 综合评估 Schema（EVAL_SCHEMA，v2.2）

```json
{
  "ats_pct": "integer (0–100)",
  "strong_matches": ["string"],
  "missing_skills": ["string"],
  "unmet_requirements": ["string"],
  "notes": "string",
  "skills_improvements": {
    "technical": ["string"],
    "certifications": ["string"],
    "soft_skills": ["string"],
    "tools": ["string"]
  },
  "resume_improvements": {
    "bullet_strength": ["string"],
    "achievements_feedback": "string",
    "metrics_suggestions": ["string"],
    "ats_keywords": ["string"]
  },
  "formatting_improvements": {
    "tone_clarity": ["string"],
    "action_verbs": ["string"],
    "layout": ["string"]
  },
  "recommendations": {
    "top_5": ["string"],
    "quick_wins": ["string"],
    "deeper_improvements": ["string"],
    "estimated_improvement_pct": "integer"
  }
}
```

> **注**：v2.1 及以前使用的 `{ "match_score": number, "strong_matches": [...], "missing_skills": [...], "notes": string }` 旧 schema 已废弃。`match_score` 现由后端计算：`match_score = ats_pct / 100`。旧数据库记录通过前端可选链（optional chaining）优雅降级渲染。

### Tailor Agent — 输出 Schema

```json
{
  "summary": "string",
  "selected_skills": ["string"],
  "tailored_experience": [...],
  "tailored_projects": [...],
  "changes_summary": "string",
  "ats_score": "number (0.0-1.0)"
}
```

---

## 附录 B：术语表

| 术语                      | 定义                                                                                                              |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Scout Agent               | AI 模块，用于解析职位描述并生成5节结构化评估报告                                                                  |
| Tailor Agent              | AI 模块，用于为特定职位重写简历要点                                                                               |
| 差距分析（gap_analysis）  | Scout 输出：含 ats_pct、strong_matches、missing_skills、unmet_requirements、5节改进建议及综合推荐                 |
| ATS 匹配百分比（ats_pct） | Scout EVAL_SCHEMA 输出：简历与职位描述的关键词匹配度，integer 0–100；存储为 match_score = ats_pct / 100           |
| ATS 评分（ats_score）     | Tailor Agent 输出：定制简历涵盖所需技能的百分比，存于 ResumeVersion.ats_score                                     |
| EvaluationReport          | 前端共享组件（`components/EvaluationReport.tsx`），渲染5节折叠式评估报告，Scout 和 Jobs 页面均复用                |
| 预估分数提升              | recommendations.estimated_improvement_pct：若执行 Top 5 建议后的预估 ATS 分数增幅                                 |
| 高分职位                  | 匹配度 ≥ HIGH_SCORE_THRESHOLD（默认 80%）                                                                         |
| 中分职位                  | 匹配度介于 MID 和 HIGH 阈值之间（默认 70–80%）                                                                    |
| 每日 Scout                | 完整流水线：抓取所有来源 → 评分所有职位 → 发送通知                                                                |
| LinkedIn Guest API        | LinkedIn 对未登录用户/搜索引擎开放的公开接口（`/jobs-guest/jobs/api/`），无需账号或 Cookie 即可抓取职位列表和详情 |
| source_raw                | 原始未修改的要点文本；用于定制可追溯性                                                                            |
| WeasyPrint                | Python 库，将 HTML/CSS 渲染为 PDF；用于生成定制简历                                                               |
| Jinja2 模板               | 简历 HTML 模板引擎；占位符由 Tailor Agent 输出填充                                                                |
| 定制 PDF                  | 针对特定职位生成的个性化简历 PDF 文件                                                                             |

---

_本规格说明书描述了 Jobseeking Agent v2.2 的已实现状态。这是一份活文档——随着功能的新增或修改，请及时更新。_

---

## 附录 D：Claude Code Agent Teams 开发指南

> 本附录专为 Claude Code Agent Teams 模式编写。所有子 Agent 在开始任何任务前**必须先读完本附录**，再结合正文对应章节执行。

---

### D.1 代码库当前状态声明

```
项目根目录：/home/zhang/projects/Jobseeking_Agent
```

**已实现（禁止重写，只允许扩展）**：

```
backend/app/
├── agents/parser.py           ✅ 已实现，禁止修改核心逻辑
├── agents/scout.py            ✅ v2.2 已重构（EVAL_SYSTEM/EVAL_SCHEMA/_evaluate()），禁止修改
├── agents/tailor.py           ✅ 已实现，禁止修改核心逻辑
├── agents/cover_letter.py     ✅ 已实现，禁止修改核心逻辑
├── scrapers/seek.py           ✅ 已实现（Playwright），禁止修改
├── scrapers/linkedin_guest.py   ✅ 已实现（LinkedIn Guest API，无需账号/Cookie），禁止修改
├── scrapers/scheduler.py      ✅ 已实现，禁止修改
├── models/                    ✅ 全部已实现，禁止修改表结构
├── routers/jobs.py            ✅ 已实现，允许新增端点，禁止修改现有端点签名
├── routers/profile.py         ✅ 已实现，禁止修改
├── routers/scrapers.py        ✅ 已实现（seek + linkedin + 任务取消），禁止修改
├── routers/notifications.py   ✅ 已实现，禁止修改
├── routers/settings.py        ✅ 已实现，禁止修改
├── routers/dashboard.py       ✅ 已实现，禁止修改
├── routers/files.py           ✅ 已实现，禁止修改
├── pdf_generator.py           ✅ 已实现，禁止修改
├── main.py                    ✅ 已实现，只允许注册新 router
├── config.py                  ✅ 已实现，允许新增变量，禁止修改现有变量
└── database.py                ✅ 已实现，禁止修改

frontend/src/                  ✅ v2.2 新增 components/EvaluationReport.tsx；Scout.tsx 和 Jobs.tsx 已更新渲染逻辑
templates/resume.html          ✅ 已实现，禁止修改
backend/tests/                 ✅ 含 test_pdf_generator.py 和 test_linkedin_guest.py，禁止删除或修改现有测试
```

> **已移除文件（不存在，禁止引用）**：`scrapers/indeed.py`（Cloudflare 拦截），`scrapers/linkedin.py`（URL 批量模式已弃用）

---

### D.2 Agent 分工表

| Agent                 | 职责                   | 负责功能      | 工作目录                |
| --------------------- | ---------------------- | ------------- | ----------------------- |
| **Backend-PDF Agent** | 实现 PDF 生成模块      | F-28、F-29    | `backend/app/`          |
| **Backend-RSS Agent** | 实现 LinkedIn RSS 抓取 | F-04b         | `backend/app/scrapers/` |
| **Frontend Agent**    | 新增 PDF 下载 UI       | F-29 前端部分 | `frontend/src/`         |
| **Test Agent**        | 编写并运行验收测试     | 所有新增功能  | `backend/tests/`        |

**并行规则**：

- Backend-PDF Agent 与 Backend-RSS Agent 可完全并行，无共享文件
- Frontend Agent 须等待 Backend-PDF Agent 完成接口定义后再启动
- Test Agent 须等待对应 Backend Agent 完成后再验收

---

### D.3 各 Agent 任务规格

#### D.3.1 Backend-PDF Agent

**任务**：实现定制简历 PDF 生成功能

**输入**：

- `resume_version.content_json`（来自数据库，结构见第5.3节）
- `data/user_profile.json`（结构见第5.4节）
- `templates/resume.html`（需新建，结构见附录 C.4）

**输出**：

- `data/resumes/tailored_{job_id}.pdf`

**需新建的文件**：

1. `backend/app/pdf_generator.py` — 参照附录 C.4 实现，不得改动
2. `backend/app/routers/files.py` — 参照附录 C.4 实现，不得改动
3. `templates/resume.html` — Jinja2 模板，参照附录 C.4

**需修改的文件**：

- `backend/app/routers/jobs.py`：在现有 `POST /{job_id}/tailor` 端点末尾追加 PDF 生成调用（禁止修改端点签名，只追加逻辑）
- `backend/app/main.py`：注册 `files` router

**接口契约（冻结，Frontend Agent 依赖此）**：

```
GET /api/files/{job_id}/resume.pdf
→ 200 application/pdf（文件流）
→ 404 { "detail": "PDF not found" }（尚未生成时）
```

`POST /api/jobs/{job_id}/tailor` 响应新增字段：

```json
{
  "resume_version": { ... },
  "ats_score": 0.87,
  "changes_summary": "...",
  "pdf_download_url": "/api/files/{job_id}/resume.pdf"  // 新增
}
```

**验收命令**（由 Test Agent 执行）：

```bash
# 1. 单元测试
PYTHONPATH=. pytest backend/tests/test_pdf_generator.py -v

# 2. 集成测试：调用 tailor 端点后验证 PDF 存在
curl -X POST http://localhost:8000/api/jobs/{job_id}/tailor
ls data/resumes/tailored_{job_id}.pdf  # 文件必须存在

# 3. 下载验证
curl -I http://localhost:8000/api/files/{job_id}/resume.pdf
# Content-Type 必须为 application/pdf

# 4. 回归测试：确保现有测试不被破坏
PYTHONPATH=. pytest backend/tests/ -v --tb=short
# 必须保持 106 个测试全部通过
```

---

#### D.3.2 LinkedIn Guest API Scraper（✅ 已完成）

> **状态**：`backend/app/scrapers/linkedin_guest.py` 已实现，禁止修改。

**实现方式**（与最初 RSS 规格不同，已演进为 Guest API 模式）：

```
步骤一：调用 LinkedIn 公开搜索接口（无需账号）
  GET /jobs-guest/jobs/api/seeMoreJobPostings/search
      ?keywords={keyword}&location={location}&f_TPR=r86400&start={offset}
  → 返回职位卡片 HTML 片段，与普通游客访问搜索页完全相同

步骤二：对每个职位调用公开详情接口
  GET /jobs-guest/jobs/api/jobPosting/{job_id}
  → 返回完整职位描述 HTML 片段，BeautifulSoup 解析为 raw_jd
```

**接口契约（已实现）**：

```
POST /api/scrapers/linkedin
请求体：
{
  "keywords": ["ML Engineer", "AI Engineer"],
  "location": "Sydney, Australia",
  "max_results": 25
}
响应：{ "task_id": "uuid" }
后续通过 GET /api/tasks/{task_id} 轮询

DELETE /api/tasks/{task_id}
→ 取消进行中的任务
```

---

#### D.3.3 Frontend Agent

**前置条件**：Backend-PDF Agent 已完成，接口契约已确认可用

**任务**：在职位详情页新增 PDF 下载按钮

**需修改的文件**：

- `frontend/src/pages/Jobs.tsx`（或对应职位详情组件）：
  - 在 Tailor Resume 按钮下方新增"下载定制简历 PDF"按钮
  - 按钮仅在 `pdf_download_url` 字段存在时显示
  - 点击后调用 `GET /api/files/{job_id}/resume.pdf` 触发浏览器下载
  - 下载中显示 loading 状态，失败时显示错误提示

**禁止修改**：

- 现有 Tailor Resume 逻辑
- 现有 Cover Letter 逻辑
- 任何其他页面组件

**UI 规范**（参照第7.2节设计规范）：

```
按钮样式：与现有 "Tailor Resume" 按钮一致
图标：下载图标（⬇）
文案："Download Tailored PDF"
位置：Tailor Resume 按钮正下方，间距 8px
```

**验收标准**：

- 点击按钮后浏览器弹出下载对话框
- 文件名为 `resume_{job_id}.pdf`
- PDF 内容与 tailored_content 一致
- 未生成 PDF 时按钮显示禁用状态（灰色）

---

#### D.3.4 Test Agent

**任务**：为所有新增功能编写测试，并执行完整回归验收

**需新建的测试文件**：

`backend/tests/test_pdf_generator.py`

```python
# 必须覆盖：
# 1. generate_resume_pdf() 正常生成文件
# 2. 输出文件为有效 PDF（文件头为 %PDF）
# 3. 模板变量正确填充（用 pypdf 读取验证关键词）
# 4. profile 字段缺失时的容错处理
# 5. 模板文件不存在时的异常处理
```

`backend/tests/test_linkedin_guest.py`

```python
# 必须覆盖：
# 1. scrape_linkedin_guest() 网络正常时返回 list[ScrapedJob]
# 2. 网络失败时返回空列表（不抛异常）
# 3. ScrapedJob 字段完整性验证（url 非空）
# 4. max_results 参数限制生效
```

**最终验收命令（全量）**：

```bash
# 全量测试，必须全部通过
PYTHONPATH=. pytest backend/tests/ -v --tb=short 2>&1 | tail -20

# 检查测试数量：新增后总数应 ≥ 116（原106 + 新增≥10）
PYTHONPATH=. pytest backend/tests/ --co -q | tail -5
```

---

### D.4 文件读写权限总表

| 文件/目录                                | 说明                                                                 |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `backend/app/agents/tailor.py`           | 🟡 v2.3 已修改（ATS 关键词注入），后续扩展允许追加，禁止修改已有规则 |
| `backend/app/agents/` 其余文件           | 🔴 只读，禁止修改                                                    |
| `backend/app/models/`                    | 🔴 只读，禁止修改表结构                                              |
| `backend/app/scrapers/seek.py`           | 🔴 只读，禁止修改                                                    |
| `backend/app/scrapers/linkedin_guest.py` | 🔴 只读，禁止修改（Guest API 实现已稳定）                            |
| `backend/app/scrapers/scheduler.py`      | 🔴 只读，允许追加抓取器调用                                          |
| `backend/app/routers/jobs.py`            | 🟡 允许新增端点，禁止修改现有端点签名                                |
| `backend/app/routers/scrapers.py`        | 🔴 只读，禁止修改                                                    |
| `backend/app/routers/files.py`           | 🔴 只读，禁止修改                                                    |
| `backend/app/routers/notifications.py`   | 🔴 只读，禁止修改                                                    |
| `backend/app/routers/settings.py`        | 🔴 只读，禁止修改                                                    |
| `backend/app/routers/dashboard.py`       | 🔴 只读，禁止修改                                                    |
| `backend/app/pdf_generator.py`           | 🔴 只读，禁止修改                                                    |
| `backend/app/main.py`                    | 🟡 只允许注册新 router                                               |
| `backend/app/config.py`                  | 🟡 允许新增变量，禁止修改现有变量                                    |
| `templates/resume.html`                  | 🔴 只读，禁止修改                                                    |
| `frontend/src/pages/Jobs.tsx`            | 🟡 允许追加 UI 元素                                                  |
| `frontend/src/` 其余文件                 | 🔴 只读                                                              |
| `backend/tests/` 现有文件                | 🔴 只读，禁止删除或修改                                              |
| `data/`                                  | 🟡 写入 PDF 允许，禁止删除                                           |

> 🟢 新建　🟡 追加/扩展　🔴 只读　🚫 禁止触碰

---

### D.5 并行开发时序

```
时间轴 →

Backend-PDF Agent  ████████████████░░░░  (实现 pdf_generator + files router)
                                    ↓
Frontend Agent                      ████  (等接口就绪后实现下载按钮)

Backend-RSS Agent  ████████████████      (完全独立，可与 PDF Agent 并行)

Test Agent                 ░░░░████████  (各 Backend Agent 完成后介入)
                                    ↓
                              最终全量回归
```

---

### D.6 Agent 启动提示词模板

将以下提示词发给各子 Agent 作为启动指令：

**Backend-PDF Agent**：

```
请阅读 /home/zhang/projects/Jobseeking_Agent/SPEC.md 中的附录C和附录D.3.1节。
你的任务是实现定制简历PDF生成功能（F-28、F-29）。
严格遵守D.4文件读写权限表。实现完成后运行D.3.1中的验收命令并报告结果。
```

**Backend-RSS Agent**：

```
请阅读 /home/zhang/projects/Jobseeking_Agent/SPEC.md 中的第4.5节和附录D.3.2节。
你的任务是实现LinkedIn RSS无登录抓取功能（F-04b）。
严格遵守D.4文件读写权限表。实现完成后运行D.3.2中的验收命令并报告结果。
```

**Frontend Agent**：

```
请阅读 /home/zhang/projects/Jobseeking_Agent/SPEC.md 中的附录D.3.3节。
Backend-PDF Agent已完成，接口契约为：GET /api/files/{job_id}/resume.pdf。
你的任务是在Jobs页面新增PDF下载按钮。严格遵守D.4文件读写权限表。
```

**Test Agent**：

```
请阅读 /home/zhang/projects/Jobseeking_Agent/SPEC.md 中的附录D.3.4节。
Backend Agent已完成实现。你的任务是编写测试并执行全量回归验收。
最终结果必须：总测试数 ≥ 116，全部通过，0个失败。
```

---

## 附录 E：求职数据分析仪表盘方案（Analytics + Data Warehouse + Tableau）

**状态**：🔲 待开发（规划阶段，讨论于 2026-07-29，尚未破土）
**目的**：为求职（Data Engineer 方向）作品集提供可展示的 SQL / 数据建模 / 云数据仓库 / BI 可视化能力证据，与 Jobseeking_Agent 现有的爬虫/API/AI Agent 能力共同构成一个完整的端到端个人项目叙事，而非另起一个孤立的 Kaggle 玩具项目。

### E.1 背景

用户计划开发一个数据分析仪表盘，用于面试/作品集展示 SQL 实战能力，并进一步扩展到 Snowflake 星型模型数据仓库 + Tableau Public 公开可视化（投递转化率、行业分布、响应时间趋势）。讨论过程中确认：

- 真实个人求职数据量小（几十条 Job 记录），且 Tableau Public 是**真公开**服务（任何人可下载底层数据），直接发布真实数据（公司名、投递状态等）有隐私风险。
- 现有 `Job`/`Application` 表缺少两块数据：行业分类字段、真实的状态变更时间线（`Application.status` 目前是从未被更新过的死字段，见 `ARCHITECTURE_REVIEW.md` §5 第 6 条）。
- 最终决定：**整条分析链路（含项目内页面）改用 Faker 生成的虚拟数据**，不使用真实求职记录，从根源解决隐私问题，同时可以自由造出行业分布、状态时间线等目前真实数据里没有的维度。

### E.2 被拒绝的方案

以下是讨论中明确排除的方案，后续开发不应重新引入，除非有新理由：

- **发布真实个人求职数据到 Tableau Public**：隐私风险不可接受（公司名、投递明细任何人可下载）。
- **只用 DuckDB、不碰 Snowflake**：DuckDB 零运维更省事，但用户看到的多个 Data Engineer JD 都点名 Snowflake，放弃会失去一个具体的简历/面试谈资。
- **Snowflake + DuckDB 双实现（同一套 DDL 适配两种方言）**：作为"设计了引擎无关的维度模型"的加分项被讨论过，但增加了额外工作量，用户选择了"只用 Snowflake，接受 30 天试用窗口"的精简版本。
- **另起一个基于 Kaggle 数据集的独立 Data Engineer 作品集项目**：讨论后判定叙事上不如现有项目——Jobseeking_Agent 已有真实的爬虫/API/AI Agent 集成，能覆盖目标 JD 中"APIs、云服务、数据摄取"等要求；Kaggle 热门数据集做星型模型是招聘方见过无数次的模板化项目，辨识度低。且该 JD 明确要求"熟练使用 LLM coding assistant 做 pipeline 开发/调试/文档"，本项目本身的 SPEC 驱动 + Claude Code 协作开发流程就是直接证据。
- **给生产用的 `Job` 表新增 `industry` 字段并用 LLM 对真实岗位批量回填**：在"改用虚拟数据"之前讨论过，因为要修改生产 schema、成本较高而被否决；改用虚拟数据后，行业标签可以在数据生成脚本里直接合成，不再需要碰生产表，因此行业分布指标被重新纳入范围。

### E.3 架构

```
Faker 虚拟数据生成脚本（一次性 / 可重跑）
   ↓ 生成 Job / Application / Company / 状态变更历史 等 OLTP 形状的数据
   ↓ 写入独立的 data/analytics_demo.db（不写入生产用的 data/db/jobseeking.db，不污染真实求职数据）
   │
   ├──→ 项目内 /analytics 页面（frontend + 新 router）
   │      原生 SQL（session.exec(text(...))）查询 data/analytics_demo.db
   │      覆盖 JOIN / GROUP BY / CTE / 窗口函数 / JSON 提取 等技巧
   │
   └──→ ETL 脚本（scripts/ 或 backend/app/analytics/ 下新目录）
          读取 data/analytics_demo.db → 转换为星型模型 → 加载进 Snowflake
                 ↓（30 天试用窗口内完成建模、查询验证、截图/文档存证）
          Snowflake（fact_application + dim_job / dim_company / dim_date）
                 ↓ 发布 Tableau **extract**（数据快照，不做实时连接）
          Tableau Public 仪表盘：投递转化率 / 行业分布 / 响应时间趋势
```

### E.4 范围边界

**包含**：
- 虚拟数据生成脚本，独立数据库文件，不接触生产 `Job`/`Application`/`ResumeVersion` 表
- 项目内新页面：`backend/app/routers/analytics.py`（原生 SQL）+ `frontend/src/pages/Analytics.tsx` + 侧边栏导航入口
- ETL 脚本：`data/analytics_demo.db` → Snowflake 星型模型（fact_application + 至少 dim_job / dim_company / dim_date）
- Tableau Public 仪表盘：投递转化率、行业分布、响应时间趋势（均基于虚拟数据）
- 仪表盘页面与仓库 README 中明确标注"合成数据集，用于技术能力演示"

**不包含**：
- 不修改生产用 `Job`/`Application` 表结构（不加 `industry` 字段、不加状态历史表到生产 schema）
- 不做 Snowflake 长期在线维护（试用期 30 天，到期后账号挂起属预期内，不做续费/迁移付费账号的安排）
- 不做 Tableau 与 Snowflake 的实时连接（只发布 extract 快照）
- 不做多用户/多数据集支持

### E.5 分析模块（沿用此前确认的 6 个 + 行业分布）

| 模块 | 承载位置 | 用到的技巧 |
|---|---|---|
| 来源 × 状态转化矩阵 | 项目内页面 | `GROUP BY` + 条件聚合 |
| 技能缺口 Top N | 项目内页面 | `json_each()` JSON 行转列 |
| 匹配分数分布直方图 | 项目内页面 | `CASE`/`CAST` 分桶聚合 |
| 岗位发现趋势 + 7 日移动平均 | 项目内页面 | 窗口函数（`ROWS BETWEEN`） |
| Tailor/投递转化率 | 项目内页面 + Tableau | 多表 `JOIN` + CTE |
| 高频出现公司 Top N | 项目内页面 | `GROUP BY` + `ORDER BY COUNT(*)` |
| 行业分布 | Tableau（虚拟数据合成的 `industry` 字段） | Snowflake 维度建模 |
| 响应时间趋势 | Tableau（虚拟数据合成的状态变更时间线） | 星型模型 + 日期维度 |

### E.6 关键约束与风险

- **Snowflake 30 天试用窗口**：无信用卡即可开通，30 天或 $400 额度先到先算；到期后账号挂起（不能查询），10 天后数据删除，除非转付费。因此必须在窗口内完成"建模 → 查询验证 → 截图/文档存证 → 发布 Tableau extract"全部动作，不能设计成长期在线依赖 Snowflake 的架构。
- **数据标注义务**：仪表盘和 README 必须清楚说明数据是合成的，不得暗示是真实求职战绩，这是诚信底线，不是可选项。
- **SQLite 方言限制**：项目内分析页用 SQLite（`json_each`、窗口函数均支持，但无 Postgres 专属函数如 `json_agg`）；ETL 到 Snowflake 时注意方言差异。

### E.7 开发时序建议（进入开发阶段时再拆细 Task）

1. 虚拟数据生成脚本 + 独立 `analytics_demo.db`
2. 项目内 `/analytics` 页面（原生 SQL，6+1 个模块）
3. ETL 脚本 + Snowflake 星型模型（需在 30 天窗口内一次性完成到发布 extract）
4. Tableau Public 发布 + README/页面数据来源标注

### E.8 Task 拆分（开发阶段，2026-07-29 拆分）

> Task 粒度 = commit 粒度。开发顺序：D01 → D02/D03（可并行）→ D04 → D05。D04 涉及 Snowflake 真实账号的 30 天试用窗口，**必须等 D01–D03 完全稳定后再开通账号启动**，避免窗口期浪费在前置阶段的调试上。

#### TASK-D01：虚拟数据生成脚本 ✅ 完成（分支 `feat/analytics/demo-data-generator`）

- **输入**：无外部输入，脚本内用常量定义规模（建议 ≥5 个行业、200+ 家虚拟公司、800+ 条虚拟 Job、300+ 条虚拟 Application，每条 Application 2-4 条状态变更记录）
- **输出**：新建 `scripts/generate_analytics_demo_data.py`；运行后在独立文件 `data/analytics_demo.db` 生成 4 张表（纯 SQL DDL，**不使用 SQLModel**——两套 SQLModel 元数据在同一进程会冲突，见 DECISIONS.md DEC-01）：
  - `demo_company(id, name, industry)`
  - `demo_job(id, source, title, company_id, location, salary_min, salary_max, match_score, gap_analysis_json, status, created_at)`
  - `demo_application(id, job_id, channel, applied_at)`
  - `demo_application_status_log(id, application_id, status, changed_at)`
- **新增依赖**：`faker`
- **约束 / 不得做**：
  - 不得读写生产库 `data/db/jobseeking.db`，两者物理隔离
  - `gap_analysis_json` 结构必须与真实 `Job.gap_analysis` 的 key（`missing_skills`/`strong_matches` 等）一致，保证 D02 的 `json_each` 查询逻辑可原样套用到真实数据
  - 脚本必须可重复运行（先 `DROP TABLE IF EXISTS` 再重建），不得追加导致重复数据
  - 数据分布需有真实感：覆盖多行业、三种 source（seek/linkedin/manual）、完整的 status 生命周期（不能全是 `new`）
- **AC**：
  - `python scripts/generate_analytics_demo_data.py` 跑完后四张表均有数据，量级符合上述规模
  - 生产库 `data/db/jobseeking.db` 内容不受任何影响

#### TASK-D02：后端 Analytics Router（原生 SQL）

- **输入**：TASK-D01 产出的 `data/analytics_demo.db`
- **输出**：新建 `backend/app/analytics_db.py`（独立 engine，指向 `analytics_demo.db`）+ `backend/app/routers/analytics.py`（6 个 GET 端点）+ `main.py` 注册路由：
  - `GET /api/analytics/funnel` — 来源 × 状态转化矩阵
  - `GET /api/analytics/skill-gaps` — 技能缺口 Top N（`json_each`）
  - `GET /api/analytics/score-distribution` — 匹配分数分布直方图
  - `GET /api/analytics/discovery-trend` — 岗位发现趋势 + 7 日移动平均（窗口函数）
  - `GET /api/analytics/conversion` — Tailor/投递转化率（JOIN + CTE）
  - `GET /api/analytics/top-companies` — 高频公司 Top N
- **约束 / 不得做**：
  - 一律 `session.exec(text(...))` 原生 SQL，**不用 SQLModel `select()`/ORM 查询构造器**（本功能的核心目的就是展示 SQL，不能藏在 ORM 后面）
  - 不得复用生产 `database.py` 的 `engine`
  - 只读，不得出现任何 INSERT/UPDATE/DELETE
  - `analytics_demo.db` 不存在时返回明确的 4xx 提示，不得 500 崩溃
- **AC**：
  - 6 个端点均可通过 `curl` 正常返回 JSON
  - `discovery-trend` 的 SQL 必须包含 `OVER (ORDER BY ... ROWS BETWEEN)`；`skill-gaps` 必须包含 `json_each`
  - 新增 pytest：至少覆盖 1 个端点 happy path + `analytics_demo.db` 缺失时的错误路径

#### TASK-D03：前端 Analytics 页面

- **输入**：TASK-D02 的 6 个接口契约
- **输出**：`frontend/src/pages/Analytics.tsx`（6 个区块对应 6 个接口）；`App.tsx` 注册 `/analytics`；`Layout.tsx` NAV_ITEMS 新增入口；`i18n/translations.ts` 补充 en/zh 文案
- **约束 / 不得做**：
  - 沿用现有页面风格（`glass-card`、`useT()`、深色模式变量），不引入新 UI 库
  - 必须挂在侧边栏可达（不得重蹈 `Scout.tsx` 无导航入口的覆辙）
- **AC**：
  - `/analytics` 从侧边栏可达
  - 6 个模块均有加载态和空态（`analytics_demo.db` 未生成时提示先跑 TASK-D01）
  - `npx tsc --noEmit` 通过

#### TASK-D04：ETL 脚本 → Snowflake 星型模型

- **输入**：`data/analytics_demo.db`；Snowflake 试用账号凭证（人工注册，30 天窗口从注册起计时）
- **输出**：`scripts/etl_to_snowflake.py`；Snowflake 侧建表：`dim_date` / `dim_company`（含 industry）/ `dim_job` / `fact_application`（含从状态变更记录算出的 `days_to_first_response`）
- **新增依赖**：`snowflake-connector-python`
- **约束 / 不得做**：
  - 凭证只能来自环境变量（新增 `SNOWFLAKE_ACCOUNT`/`SNOWFLAKE_USER`/`SNOWFLAKE_PASSWORD`/`SNOWFLAKE_WAREHOUSE`/`SNOWFLAKE_DATABASE`，写入 `.env.example` 但不写真实值），不得硬编码或提交到 git
  - 不引入 `pandas`；用标准库 `sqlite3` 读 + connector 的 `cursor.executemany` 写，控制依赖体积
  - **必须等 D01–D03 稳定后再开通 Snowflake 账号启动本 Task**，避免 30 天窗口浪费
- **AC**：
  - Snowflake 内 4 张表行数与源库一致
  - 人工在 Snowflake Web UI 跑 1-2 条验证查询（如按 industry 分组求平均 match_score）并截图存档到 `docs/snowflake_verification/`

#### TASK-D05：Tableau Public 发布 + 数据来源标注

- **输入**：TASK-D04 产出的 Snowflake 星型模型
- **输出**：`scripts/export_for_tableau.py`（导出 Tableau Public 可直接读取的文件）；README 新增"数据来源说明"；Analytics 页面加"合成数据集"标注
- **约束 / 不得做**：
  - Tableau Public Desktop 的建图/发布是 GUI 操作，不可自动化，本 Task 只交付导出脚本 + 人工 checklist
  - 不得用实时连接（Snowflake 30 天后不可用），必须是静态导出文件 / extract
- **AC**：
  - 导出文件能被 Tableau Public Desktop 正常读取（人工验证）
  - 发布的 Tableau Public 链接、README、Analytics 页面三处均清楚标注"合成数据集"
  - 投递转化率 / 行业分布 / 响应时间趋势三个目标图表在 Tableau Public 上可见

_本附录为规划记录，非实现文档。进入开发前需按 CLAUDE.md 流程重新走一遍 Interpretation Confirmation，并将各阶段拆成自包含的 TASK-XX（输入/输出/约束/禁止事项/AC）。_
