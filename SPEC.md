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

#### TASK-D02：后端 Analytics Router（原生 SQL） ✅ 完成（分支 `feat/analytics/demo-data-generator`）

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

#### TASK-D03：前端 Analytics 页面 ✅ 完成（分支 `feat/analytics/demo-data-generator`）

- **输入**：TASK-D02 的 6 个接口契约
- **输出**：`frontend/src/pages/Analytics.tsx`（6 个区块对应 6 个接口）；`App.tsx` 注册 `/analytics`；`Layout.tsx` NAV_ITEMS 新增入口；`i18n/translations.ts` 补充 en/zh 文案
- **约束 / 不得做**：
  - 沿用现有页面风格（`glass-card`、`useT()`、深色模式变量），不引入新 UI 库
  - 必须挂在侧边栏可达（不得重蹈 `Scout.tsx` 无导航入口的覆辙）
- **AC**：
  - `/analytics` 从侧边栏可达
  - 6 个模块均有加载态和空态（`analytics_demo.db` 未生成时提示先跑 TASK-D01）
  - `npx tsc --noEmit` 通过

#### TASK-D04：ETL 脚本 → Snowflake 星型模型 ✅ 完成（分支 `feat/analytics/demo-data-generator`，验证记录见 `docs/snowflake_verification/`）

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

---

## 附录 F：v3.0 升级方案（本地应用 + GitHub MCP + 确定性 ATS 模拟器）

**规划日期**：2026-08-19
**状态**：`planning` — 待人工确认 AC 后进入开发
**关联**：本附录直接回应 §8.6「ATS 评分说明（重要限制）」中记录的方法论缺陷

---

### F.1 背景：这次升级要解决的真正问题

§8.6 已明确记录现有评分的局限：`match_score` 是 **Gemini 主观估算**的"它认为 ATS 会怎么打分"，而非真实 ATS 解析结果。这带来一个根本性问题：

> 该分数可能与"这份简历写得好不好"高度相关，但与"真实 ATS 会不会把它筛掉"**未必相关**。

真实 ATS 淘汰简历的两个高频原因，LLM 打分**结构上无法覆盖**：

| 真实失败模式 | LLM 为何看不见 |
|---|---|
| **解析失败** — 表格、多栏、图标、页眉页脚放联系方式，导致解析器读出乱码或空白 | 模型看到的是已渲染好的文本，不是"这份 PDF 被笨拙解析器读完会变成什么样" |
| **字面关键词匹配** — JD 写 `Kubernetes`、简历写 `K8s`，字符串级匹配直接 miss | 模型的语义理解会认为"这明显是同一个东西"，从而高估命中率 |

**因此 v3.0 的核心不是"让 LLM 打分更准"，而是新增一套完全不依赖 LLM 的确定性评估（模块 C），与现有 LLM 定性分析并列存在、互相校验。** 这是本次升级中唯一决定"项目是否真正有效"的模块，其余模块为配套的形态与数据源升级。

---

### F.2 被拒绝的方案（Rejected Approaches）

> 以下方案在需求讨论中被明确拒绝，**不得在后续开发中重新引入**。

| 方案 | 拒绝理由 |
|---|---|
| **Agent 自主投递申请** | LinkedIn / Seek 服务条款明确禁止自动化投递，触发风控轻则限流重则封号。且投递是**不可逆的外部动作**，后果直接落在用户真实求职声誉上。改为：系统批量推送「岗位 + 已定制简历」，由人类在平台上自行提交 |
| **邮箱监听自动更新投递状态**（IMAP / Gmail API） | 用户明确表示暂不接受将邮箱访问权交给 agent。投递结果追踪仅保留「人类零摩擦确认」一层 |
| **提升 LLM 打分准确度以解决 ATS 评分问题** | 治标不治本。LLM 无论如何优化都无法评估"排版解析风险"与"字面匹配率"，这是模型输入形态决定的结构性盲区，只能由确定性模块补足 |
| **对系统生成的 PDF/DOCX 做解析度校验** | 文件生成模块因产出排版质量不达投递标准已被搁置（见 F.3 依赖冲突说明）。若以其产出为校验对象，模块 C 将被搁置模块阻塞。改为校验**用户实际上传/投递的简历文件** |
| **用 embedding / 语义相似度做关键词匹配** | 与本模块目的直接矛盾。模块 C 的价值恰恰在于模拟"真实 ATS 的字符串级匹配"，引入语义相似度会退化成又一个"LLM 式的宽容判断"，失去与 LLM 分数对照的意义 |
| **定时自动抓取（APScheduler 每日 9:00 触发，F-08）** | 桌面应用形态下需常驻托盘进程才能成立，为一个非核心功能引入常驻进程的复杂度与用户心智负担不划算。**全面改为用户手动开启抓取**。相关的 `SCHEDULER_*` 环境变量、`backend/app/scheduler.py` 一并移除 |
| **Snowflake 星型模型 / Tableau Public 发布（附录 E TASK-D04/D05）** | 用户暂无能力维护，且 Snowflake 试用窗口有限。该线整体搁置，不在 v3.0 范围内 |
| **文件生成（PDF/DOCX）排版质量打磨** | 主动搁置。当前产出不符合"可直接投递"标准，但优先级低于 ATS 评分有效性 |

---

### F.3 已识别的依赖冲突（进入开发前必须确认）

| # | 冲突 | 处置 |
|---|---|---|
| F-CONF-01 | 模块 C 的解析度校验需要一份 PDF/DOCX 作为输入，而文件生成模块已搁置 | **校验对象改为用户上传的简历文件**（`data/resumes/` 下用户原始上传件）。既解耦搁置模块，也更贴近真实场景——校验的是真正会被 ATS 读到的那个文件 |
| F-CONF-02 | 模块 A 桌面化后为「用户点开才跑」，而 F-08「每日 9:00 自动抓取」依赖 APScheduler 进程常驻 | **已决策（2026-08-19）：舍弃定时抓取，全面改为用户手动开启。** 不做托盘常驻。由 TASK-A01 执行移除，该 Task 独立于打包工作，可提前单独实施。附带收益：消除「两个同名 `scheduler.py`」的既有技术债 |
| F-CONF-03 | 模块 B 的 GitHub 技能推断会写入 `UserProfile`，与现有 `Resume.tsx` 增量合并逻辑存在重叠 | 复用现有合并规则（years 取大值、按 key 去重、占位符不覆盖），**不得新写一套合并逻辑** |

---

### F.4 架构变更总览

```
形态变更：Web 服务（公网可达 + 常驻定时任务）  →  本地桌面应用（单机 + 全手动触发）
  副作用 1：§8.3 安全性中「无鉴权」风险项随之消解——不再有公网暴露面
  副作用 2：APScheduler 整条链路移除，「两个同名 scheduler.py」技术债一并消除

数据源新增：GitHub MCP  →  ProfileSyncAgent  →  (diff 提议) → 人工确认 → UserProfile

评分体系（核心变更）：
  现状：Gemini ats_pct  ──────────────────────────▶  match_score（单一主观分数）

  v3.0：Gemini ats_pct        ──▶ 定性分析（保留，仍用于 5 段评估报告）
        ATSSimulator（新增）  ──▶ deterministic_ats_score（确定性、可复现）
                                    ├── parseability_score  解析度
                                    └── keyword_match_score 字面命中率
        两分数并列展示 + 差异解读（差异本身即为最有价值的洞察）

投递闭环：批量推送（岗位+已定制简历） → 人类平台自行提交 → 消息内一键确认 → Application 状态机
```

---

### F.5 模块 C：确定性 ATS 模拟器 【P0 · 核心】

**目标**：新增 `backend/app/ats/` 子包，提供完全不依赖 LLM、可复现、可单元测试的 ATS 模拟评分，补足 §8.6 记录的方法论缺陷。

#### TASK-C01：解析度校验器（parseability checker）

- **输入**：用户上传的简历文件路径（`data/resumes/` 下 PDF/DOCX），及其经 `ResumeParser` 得到的结构化 `UserProfile`
- **输出**：新建 `backend/app/ats/parseability.py`，导出 `check_parseability(file_path, expected_profile) -> ParseabilityReport`
  - `ParseabilityReport`：`score`(0-100)、`extracted_char_count`、`missing_fields`(list)、`warnings`(list[str]，如"检测到多栏排版，联系方式可能位于页眉")
- **实现要点**：复用现有 `ResumeParser._extract_pdf` / `_extract_docx` 重新抽取纯文本，与 `expected_profile` 中的关键字段（姓名、各项技能名、公司名、学校名）逐一比对，统计**抽取后仍能找到**的比例
- **约束 / 不得做**：
  - 纯确定性，**不得调用任何 LLM**
  - **不得**以系统生成的 PDF/DOCX 为校验对象（见 F-CONF-01）
  - 不得引入新的 PDF 解析库，复用现有 `pypdf` / `python-docx`
- **AC**：
  - 同一文件重复调用 10 次，`score` 完全一致（确定性验证）
  - 给定一份多栏/表格排版的简历样本，能检出字段丢失并产生 warning
  - 给定一份单栏纯文本简历，`score ≥ 90`
  - 新增 pytest 覆盖：正常 PDF、正常 DOCX、损坏文件、字段全丢失四种情况

#### TASK-C02：字面关键词匹配引擎

- **输入**：JD 原文、简历纯文本、Scout 已产出的 `gap_analysis.resume_improvements.ats_keywords`
- **输出**：新建 `backend/app/ats/keyword_match.py`，导出 `match_keywords(jd_text, resume_text, keywords) -> KeywordMatchReport`
  - 报告含：`score`(命中率 %)、`hits`(list)、`misses`(list)、`alias_hits`(list[tuple]，记录经别名表命中的项)
  - 同时新建可配置别名表 `backend/app/ats/aliases.py`（如 `K8s↔Kubernetes`、`JS↔JavaScript`、`ML↔Machine Learning`）
- **约束 / 不得做**：
  - **严禁使用 embedding / 语义相似度 / LLM 判断**——本模块的全部价值在于模拟真实 ATS 的字符串级匹配（见 F.2）
  - 匹配需大小写不敏感、处理词边界（`Java` 不得命中 `JavaScript`）
  - 别名表必须是独立可维护的数据文件，不得散落在匹配逻辑中
- **AC**：
  - `Kubernetes`(JD) vs `K8s`(简历) 经别名表命中，并在 `alias_hits` 中标注
  - `Java`(JD) vs 仅含 `JavaScript` 的简历 → 判定为 miss（词边界验证）
  - 同输入重复调用结果完全一致
  - 新增 pytest 覆盖：精确命中、别名命中、词边界误命中、空关键词列表

#### TASK-C03：综合报告与双分数对照展示

- **输入**：C01 与 C02 的输出
- **输出**：
  - `backend/app/ats/simulator.py`：`simulate_ats(...)` 聚合两项得出 `deterministic_ats_score`
  - 数据模型新增字段：`ResumeVersion.deterministic_ats_score`(float)、`ResumeVersion.ats_report`(JSON)
  - 新增端点 `POST /api/ats/simulate`
  - 前端在展示 `match_score` 处**并列**展示两个分数及差异解读文案
- **约束 / 不得做**：
  - **不得**用确定性分数覆盖或替换现有 `match_score`，两者并存、各自标注来源
  - 差异解读文案须具体可执行（如"字面关键词覆盖率仅 42%，建议在技能区补充 JD 原词"），不得输出"分数偏低"这类无信息量文案
  - §8.6 要求的"AI 估算，仅供参考"标注对 LLM 分数**继续保留**
- **AC**：
  - 同一 (简历, JD) 组合，`deterministic_ats_score` 可复现
  - 前端能同时看到两个分数；当差值 > 20 时展示差异解读
  - 新增 pytest 覆盖端点 happy path + 简历文件缺失的错误路径

#### TASK-C04：将确定性分数接入 Tailor 闭环（Evaluator-Optimizer）

- **输入**：TailorAgent 当前输出 + C03 的确定性评分
- **输出**：改造 `TailorAgent.run()`，形成有界迭代：生成 → 确定性评分 → 若低于阈值则携带 `misses` 反馈重写 → 重新评分
- **约束 / 不得做**：
  - **必须有硬性最大迭代次数**（默认 2，可配置），达上限即返回当前最佳版本，**不得无限循环**
  - 反馈信号使用**确定性分数**，不得再用 `_eval_ats_score` 的 LLM 自评来驱动重写决策（避免"用一个模型的主观判断评估另一个模型的主观判断"）
  - 每轮版本均须落库保留，**不得覆盖**历史 `ResumeVersion`
  - 现有 `_validate_bullets` 数字幻觉校验必须在每一轮都执行，不得因迭代而跳过
- **AC**：
  - 迭代次数达上限时正常返回，日志记录实际轮数
  - 迭代后 `deterministic_ats_score` 不低于首轮（若低于则返回首轮版本）
  - 数据库中可查到同一 job 的多个版本及各自分数
  - 新增 pytest：mock 掉 LLM 调用，验证迭代次数上限与"取最优版本"逻辑

---

### F.6 模块 D：投递追踪闭环（人工确认层）【P0】

**目标**：修复 `Application.status` 死字段（现状：创建后恒为 `pending`，导致 §2.6 F-56 申请回复率统计永远输出 0%），建立「批量推送 → 人类平台自行提交 → 零摩擦确认」闭环。

#### TASK-D01：Application 状态机接通

- **输入**：现有 `Application` 模型
- **输出**：将 `status` 由自由字符串改为枚举 `ApplicationStatus`：`ready`(AI 已备好) → `applied`(人类已投递) → `responded` / `interview` / `rejected`；新增 `PUT /api/applications/{id}/status`
- **约束 / 不得做**：
  - 需处理存量数据迁移（现有 `"pending"` 记录映射为 `ready`）
  - **不得**引入任何自动推断状态的逻辑（邮箱监听已被拒绝，见 F.2）
  - 修正 `dashboard.py` 中基于该字段的 `response_rate` 统计，使其反映真实数据
- **AC**：
  - 状态流转可通过 API 完成，非法流转返回 4xx
  - `GET /api/dashboard/advisor` 的 `response_rate` 在有数据时不再恒为 0%
  - 新增 pytest 覆盖：正常流转、非法流转、存量数据迁移

#### TASK-D02：批量推送与零摩擦确认

- **输入**：状态为 `ready` 的 Application 集合
- **输出**：批量推送消息（含岗位、匹配分数、已定制简历下载入口）；推送消息内提供一键「✅ 已投递 / ⏭ 跳过」交互，回调直接更新状态
- **约束 / 不得做**：
  - **不得**实现任何形式的自动提交（见 F.2）
  - 确认动作必须可在消息端完成，**不得要求用户返回应用内操作**（摩擦成本是本 Task 成败关键）
  - 复用现有 `notifications.py` 的 webhook 双格式适配，不得新起一套推送通道
- **AC**：
  - 推送消息含岗位、分数、简历入口三要素
  - 点击确认后 Application 状态实际变更，可在 Dashboard 查得
  - webhook 未配置时降级为应用内列表展示，不报错

---

### F.7 模块 B：GitHub MCP 档案同步 【P1】

**目标**：将 §9 v3.0 愿景中「作品集集成 — 自动将 GitHub 项目关联到技能和经历」落地，使 `UserProfile` 从纯手工维护变为可被动同步。

#### TASK-B01：GitHub MCP 客户端接入

- **输入**：GitHub 官方 MCP server；用户 GitHub token（环境变量，写入 `.env.example` 但不得含真实值）
- **输出**：新建 `backend/app/mcp/github_client.py`，封装 `list_repos` / `get_repo_languages` / `get_recent_commits` / `read_readme` 四项调用
- **约束 / 不得做**：
  - **不得**自行封装 GitHub REST API，必须走 MCP server（本 Task 的目的之一即验证工具可插拔性）
  - token 只能来自环境变量，不得硬编码或提交
  - 只读，不得有任何写 GitHub 的操作
- **AC**：四项调用均可返回真实数据；token 缺失时返回明确 4xx 而非 500

#### TASK-B02：技术栈与活跃时长推断

- **输入**：B01 的仓库数据
- **输出**：`backend/app/agents/profile_sync.py`，从语言统计 + 依赖文件（`package.json`/`pyproject.toml`/`requirements.txt`）推断技术栈；从 commit 时间跨度反推各技术的**活跃使用时长**
- **约束 / 不得做**：
  - 技能 `years` 必须优先采用 **commit 时间戳推算的客观值**，不得沿用 `ResumeParser` 中 LLM 主观估计的方式（该字段现状为模型脑补，本 Task 即为校正它）
  - fork 的仓库默认排除，可配置
- **AC**：给定一个真实账号，产出的技术栈列表与实际仓库语言分布一致；`years` 有 commit 时间跨度作为依据，可在报告中回溯

#### TASK-B03：diff 提议与人工确认合并

- **输入**：B02 推断结果 + 现有 `UserProfile`
- **输出**：产出**变更提议 diff**（新增技能 / years 变化 / 新增项目），前端展示后由人类逐项确认合并
- **约束 / 不得做**：
  - **严禁自动覆盖 `UserProfile`**——必须人工确认，与项目既有人机边界保持一致
  - 合并规则复用 `Resume.tsx` 现有逻辑（years 取大值、按 key 去重、占位符不覆盖），**不得新写一套**（见 F-CONF-03）
- **AC**：diff 可视、可逐项接受/拒绝；拒绝的项不写入；手动编辑过的字段不被静默覆盖

---

### F.8 模块 A：本地桌面应用打包 【P2】

**目标**：形态由「Web 服务 + 常驻定时任务」改为「单机桌面应用 + 全手动触发」。副作用：§8.3 中「22 个端点全部无鉴权 + 公网部署」的风险项随公网暴露面消失而消解。

#### TASK-A01：移除定时调度，全面改为手动触发 【优先级 P1，独立于打包，可提前实施】

- **输入**：现有 `backend/app/scheduler.py`（APScheduler 包装）、`backend/app/scrapers/scheduler.py`（业务逻辑 `run_daily_scout()`）
- **输出**：
  - 删除 `backend/app/scheduler.py`；`main.py` 的 `lifespan` 中移除 `start_scheduler()` / `stop_scheduler()` 调用
  - **保留** `run_daily_scout()` 业务逻辑，但重命名以消除语义误导（建议 `scrapers/scheduler.py` → `scrapers/batch_scrape.py`，`run_daily_scout()` → `run_batch_scrape()`）
  - 移除 `SCHEDULER_ENABLED` / `SCHEDULER_HOUR` / `SCHEDULER_MINUTE` 三个环境变量及 `config.py` 中对应常量；同步清理 `.env.example`、`render.yaml`、README
  - 前端 Settings 页移除调度时间配置项；Notifications 页的「手动触发」入口保留并提升为主入口
- **约束 / 不得做**：
  - **不得**删除 `run_daily_scout()` 的业务逻辑本身——它仍是「一次跑完 Seek + LinkedIn 并汇总」的有效入口，仅调用方式由定时改为手动
  - **不得**保留任何形式的常驻后台调度（含托盘常驻、系统级 cron 注册）
  - `push_daily_summary()` 保留，但语义由「每日定时摘要」改为「本次批量抓取完成摘要」，函数名与文案需同步调整
  - 移除 `apscheduler` 依赖前须确认无其他引用
- **AC**：
  - 全局搜索无 `apscheduler` / `SCHEDULER_` 残留
  - 应用启动后不再有任何后台定时任务，日志中无调度器相关输出
  - 手动触发批量抓取功能完整可用，抓取结束后推送摘要
  - 现有测试全部通过；涉及调度的测试相应移除或改写

#### TASK-A02：pywebview 应用外壳

- **输出**：`desktop/main.py` — 启动本地 FastAPI 进程并以原生窗口加载，不经由系统浏览器
- **约束**：不得引入 Node/Rust 工具链（已评估 Tauri：需将 PyInstaller 产物作为 sidecar，多一套构建流程，投入产出比不足）
- **AC**：双击启动后出现原生窗口，全部页面功能与浏览器访问一致

#### TASK-A03：PyInstaller 打包与 Playwright 引导

- **输出**：单文件可执行程序构建脚本；首次启动时以进度界面引导下载 Chromium 组件
- **约束 / 不得做**：
  - **不得**将 Chromium 二进制直接打进产物（体积不可接受）
  - **不得**假设最终用户会自行执行 `playwright install chromium` 命令行
- **AC**：在无 Python 环境的干净机器上可运行；首启动能完成浏览器组件引导；引导失败时抓取功能优雅降级而非崩溃

> 原「TASK-A03：调度模型决策」已因 F-CONF-02 于 2026-08-19 决策完毕而取消，其执行内容并入 TASK-A01。

---

### F.9 开发时序与优先级

| 阶段 | Task | 优先级 | 说明 |
|---|---|---|---|
| 1 | C01 → C02 | **P0** | 两者独立，可并行；构成确定性评分基座 |
| 2 | C03 | **P0** | 依赖 C01+C02 |
| 3 | D01 → D02 | **P0** | 独立于 C，可与阶段 1-2 并行；修复既有死字段 |
| 4 | C04 | P1 | 依赖 C03 |
| 5 | **A01** | **P1** | **移除定时调度。独立于其余所有 Task，随时可插入执行**；建议尽早做，可消除既有技术债并简化后续打包 |
| 6 | B01 → B02 → B03 | P1 | 严格串行 |
| 7 | A02 → A03 | P2 | 桌面打包，建议在功能稳定后进行 |

**建议起点**：C01 + C02。二者是整个 v3.0 价值主张的地基，且完全不依赖任何被搁置模块，可独立验证成效。
**可并行的低成本收尾**：A01 与 D01 均为独立的「清理既有技术债」型 Task，可在主线开发的任意间隙插入。

---

### F.10 与既有章节的关系

- **§8.6 ATS 评分说明（重要限制）**：本附录 F.5 即为该限制的解决方案。待模块 C 合并后，需按 CLAUDE.md 流程以独立 commit 更新 §8.6，补充确定性评分的说明——**在功能完成前不得预先修改该节**
- **§9 v3.0 长期愿景**："作品集集成"由模块 B 落地；"多用户支持/云端托管"与模块 A 的单机形态方向相反，需在 v3.0 完成后重新评估
- **§2.1 F-08（每日自动抓取）**：因 F-CONF-02 决策已废止，待 TASK-A01 合并后须以独立 commit 将其状态改为「❌ 已移除（改为手动触发）」——**功能完成前不得预先修改**
- **§2.5 F-42（每日摘要推送）**：语义变更为「批量抓取完成摘要」，随 TASK-A01 一并更新
- **§4.6 后台任务模式**、**§10.2 环境变量**：均含 APScheduler / `SCHEDULER_*` 描述，随 TASK-A01 更新
- **附录 E（Analytics/Snowflake）**：整体搁置，不在 v3.0 范围内

---

_本附录为规划记录，非实现文档。各 Task 的 AC 需经人工确认后方可进入开发；开发过程遵循 CLAUDE.md：一 Task 一 commit、分支命名 `feat/<module>/<desc>`、一分支一 PR、当前 PR 未合并不得开始下一 Task。_

---

## 附录 G：LLM Provider 迁移（Gemini → DeepSeek-V4）

**规划日期**：2026-08-19
**状态**：`planning` — 仅 G01 已拆分到可开发粒度，G02–G04 待 G01 结果验证后再拆
**决策**：先迁移 `ResumeParser` 单点验证可行性，通过后逐个迁移其余 3 个 agent（`ScoutAgent` → `TailorAgent` → `CoverLetterAgent`），**不做大爆炸式整体替换**

### G.0 范围与前提（未经验证，不得假设）

> 按 CLAUDE.md「Never fill in API documentation links or versions；human 负责核实外部依赖有效性」，以下事项**必须由人工在开发前自行核实**，本 SPEC 不代为验证或假设结果：
> - DeepSeek-V4 API 的 `response_format` / structured output 能力，能否等价替代 Gemini `types.Schema` 的 `required` 字段强制、嵌套 object、`enum` 约束
> - 是否存在等价于 `response_mime_type="application/json"` 的强 JSON 输出保证，还是仅能靠 prompt 约束（若是后者，需重新评估 §8.6 类似的"输出不稳定"风险是否会在新 provider 上更严重）
> - API 调用方式（SDK 还是 OpenAI 兼容 REST）、鉴权方式、速率限制

**本次迁移不解决、不涉及**：
- 迁移动机（成本 / 性能 / 其他）未明确记录，不影响本附录的技术拆分，但如涉及"是否要保留 Gemini 作为 fallback"这类产品决策，需另行确认
- 是否引入 provider 抽象层（如 `LLMClient` 统一接口）——四个 agent 现状是各自独立持有 `genai.Client()` 实例，逐个迁移不强制要求先建抽象层。按 YAGNI 原则**暂不做**，若迁移到第二、第三个 agent 时发现重复样板代码明显，届时再补一层，不预先设计

### TASK-G01：ResumeParser 迁移至 DeepSeek-V4（验证性 Task）

- **目的**：用四个 agent 里 schema 最简单的一个（`PROFILE_SCHEMA`，无深层嵌套 enum 逻辑）做迁移可行性验证，其结果决定 G02–G04 是否继续、以及要不要调整迁移策略
- **输入**：现有 `backend/app/agents/parser.py`；人工已核实的 DeepSeek-V4 API 文档（见 G.0，本 Task 开始前必须完成）
- **输出**：
  - 改造 `ResumeParser.__init__` 与 `parse_text()`/`parse_file()` 内部调用，替换为 DeepSeek-V4
  - 新增环境变量 `DEEPSEEK_API_KEY`（写入 `.env.example`，不含真实值），`config.py` 新增对应读取
  - **保留** `GEMINI_API_KEY` 及其读取逻辑不变——本 Task 只动 `ResumeParser` 一个 agent，其余三个仍用 Gemini，两个 key 需同时存在
  - 产出一份迁移记录（追加进 `DECISIONS.md`）：记录 schema 约束能力的实测差异、是否需要额外的输出校验兜底（类比 `scout.py` 的 null 归一化经验）
- **约束 / 不得做**：
  - **不得**改动 `PROFILE_SCHEMA` 的字段定义本身（技能等级判定规则、years 推断规则等 prompt 设计保持不变），本 Task 只换底层调用，不做 prompt 层面的同步优化——避免"换模型"和"改 prompt"两件事混在一次改动里，出问题时无法定位是哪一层导致
  - **不得**改动 `profile.py` 路由层对 `ResumeParser` 的调用方式（对外接口不变）
  - 若发现 DeepSeek-V4 的结构化输出约束力明显弱于 Gemini（如无法保证 `required` 字段一定存在），**不得**跳过校验强行合并，必须在代码层补一层类似 `scout.py` 的 `or default` 兜底，并在 `DECISIONS.md` 中记录原因
- **AC**：
  - `POST /api/profile/upload-resume`、`POST /api/profile/parse-resume` 两个端点在切换后行为不变（返回结构与现状一致）
  - 现有 `backend/tests/test_*.py` 中涉及 ResumeParser 的用例全部通过（mock 调整为 mock DeepSeek 客户端而非 Gemini）
  - 新增至少 3 组真实简历文本的人工比对：DeepSeek 输出 vs 原 Gemini 输出，记录字段级差异（不要求完全一致，但需人工判断"是否可用"）
  - `DECISIONS.md` 中新增一条记录，写明本次验证结论与是否建议继续 G02

### TASK-G02 / G03 / G04：ScoutAgent / TailorAgent / CoverLetterAgent 迁移

> **暂不拆分到 Task 粒度。** 待 G01 完成并给出结论后，根据实际发现的 API 差异（尤其是结构化输出约束力）重新评估这三个 agent 的迁移方案——`TailorAgent` 的 `TAILOR_SCHEMA` 含嵌套数组对象、`ScoutAgent` 的 `EVAL_SCHEMA` 是四个 agent 里最复杂的一个（5 段嵌套结构），二者的风险远高于 `ResumeParser`，不应在 G01 结果出来前预先假设方案。

### G.5 与既有内容的关系

- 与附录 F 相互独立，两条线可并行推进，无依赖关系
- 若 G01 验证后发现 DeepSeek-V4 无法满足结构化约束，**回退方案**是保留 Gemini 现状，附录 G 到此为止——这不是失败，是这个 Task 存在的目的（用最小成本验证一个有风险的假设）
