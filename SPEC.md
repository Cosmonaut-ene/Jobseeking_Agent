# 求职助手系统 — 产品规格说明书

**版本**：2.0
**状态**：已实现
**最后更新**：2026年3月4日
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

| 痛点 | 解决方案 |
|---|---|
| 每天查看招聘网站 | 每天上午9点自动抓取（Seek、Indeed、LinkedIn） |
| 低相关度职位噪音 | AI 评分 — 只显示匹配度 ≥70% 的职位 |
| 每份申请使用通用简历 | 基于 LLM 的简历定制（针对 ATS 优化） |
| 求职信从零开始 | 根据定制简历+职位描述自动生成 |
| 不知道该学什么 | 仪表板技能差距分析（基于最近所有职位） |
| 申请跟踪困难 | 集成状态追踪 + 跟进提醒 |

---

## 2. 功能需求

### 2.1 职位发现（抓取）

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-01 | Seek.com.au 抓取器（关键词+地点+日期筛选） | P0 | ✅ 完成 |
| F-02 | Indeed.com.au 抓取器（关键词+地点+日期筛选） | P0 | ✅ 完成 |
| F-04 | LinkedIn URL 批量解析（用户提供 URL，系统自动抓取详情） | P1 | ✅ 完成 |
| F-04b | LinkedIn RSS 无登录搜索（公开职位，无封号风险） | P2 | 🔲 待开发 |
| F-05 | 每次抓取可配置最大结果数 | P1 | ✅ 完成 |
| F-06 | 基于职位 URL 去重（跳过已见职位） | P0 | ✅ 完成 |
| F-07 | 通过粘贴手动录入职位（Scout 页面） | P1 | ✅ 完成 |
| F-08 | 在可配置小时自动触发每日抓取（APScheduler） | P0 | ✅ 完成 |

### 2.2 AI 匹配与评分（Scout Agent）

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-10 | 解析原始职位描述 → 结构化字段（职位、公司、地点、薪资、技能） | P0 | ✅ 完成 |
| F-11 | 对候选人与用户简历的匹配度打分（0.0–1.0） | P0 | ✅ 完成 |
| F-12 | 差距分析：强匹配项、缺失技能、备注 | P0 | ✅ 完成 |
| F-13 | 自动过滤：丢弃 <70%，保存 70–100% | P0 | ✅ 完成 |
| F-14 | 可配置评分阈值（HIGH_SCORE、MID_SCORE） | P1 | ✅ 完成 |
| F-15 | 匹配度 ≥80% 时立即推送通知 | P0 | ✅ 完成 |

### 2.3 简历管理

> **语言要求**：简历所有内容（摘要、工作经历、项目描述、技能列表）均以**英文**输出。Tailor Agent 的定制结果亦为英文。

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-20 | 上传 PDF/DOCX 简历 → AI 提取结构化档案 | P0 | ✅ 完成 |
| F-21 | 粘贴简历文本 → AI 提取结构化档案 | P0 | ✅ 完成 |
| F-22 | 档案增量合并（新增+现有，不覆盖） | P1 | ✅ 完成 |
| F-23 | 6 标签页档案编辑器（基本、技能、教育、经历、项目、偏好） | P1 | ✅ 完成 |
| F-24 | 按职位的 LLM 简历定制（关键词优化，不捏造） | P0 | ✅ 完成 |
| F-25 | 每个定制版本的 ATS 评分 | P1 | ✅ 完成 |
| F-26 | 变更摘要（修改了什么） | P1 | ✅ 完成 |
| F-27 | 来源可追溯性：每条定制要点关联原始文本 | P1 | ✅ 完成 |

### 2.4 求职信生成

> **语言要求**：求职信（主题行+正文）均以**英文**输出，面向澳大利亚雇主。

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-30 | 根据定制简历+职位描述自动生成求职信 | P0 | ✅ 完成 |
| F-31 | 生成邮件主题行 | P1 | ✅ 完成 |
| F-32 | 正文：3段，不超过250字，不捏造 | P0 | ✅ 完成 |
| F-33 | 生成时自动创建申请记录 | P1 | ✅ 完成 |

### 2.5 通知系统

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-40 | Discord 频道通知（通过 OpenClaw webhook 推送） | P0 | ✅ 完成 |
| F-41 | 高分（≥80%）职位立即推送 | P0 | ✅ 完成 |
| F-42 | 每日摘要推送：抓取统计 + 热门职位 | P0 | ✅ 完成 |
| F-43 | 手动测试通知 | P1 | ✅ 完成 |
| F-44 | 通过 UI 手动触发每日 Scout | P1 | ✅ 完成 |

### 2.6 仪表板与分析

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-50 | 按状态统计职位数（新、已查看、已申请、面试、录用、拒绝） | P0 | ✅ 完成 |
| F-51 | 按来源统计职位数（Seek、Indeed、LinkedIn、手动） | P1 | ✅ 完成 |
| F-52 | 评分分布统计（高分/中分数量） | P1 | ✅ 完成 |
| F-53 | AI 顾问报告：技能差距分析 + 市场摘要 | P1 | ✅ 完成 |
| F-54 | 顾问 Agent 推荐行动 | P1 | ✅ 完成 |
| F-55 | 申请跟进提醒（逾期追踪） | P1 | ✅ 完成 |
| F-56 | 申请回复率统计 | P2 | ✅ 完成 |

### 2.7 申请追踪

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-60 | 职位状态生命周期（新建→已查看→已申请→面试→录用/拒绝） | P0 | ✅ 完成 |
| F-61 | 申请记录（渠道：邮件/一键申请/手动） | P1 | ✅ 完成 |
| F-62 | 每份申请的跟进日期 | P1 | ✅ 完成 |
| F-63 | 申请备注 | P2 | ✅ 完成 |

### 2.8 设置与配置

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-70 | 通过 UI 设置 Gemini API Key（写入 .env） | P0 | ✅ 完成 |
| F-71 | 通过 UI 配置 Discord 频道 ID | P1 | ✅ 完成 |
| F-72 | 通过 UI 配置评分阈值 | P1 | ✅ 完成 |
| F-73 | 通过 UI 启用/禁用调度器 + 设置运行时间 | P1 | ✅ 完成 |

---

## 3. 用户故事

### 史诗1：首次设置

**US-01** — 作为新用户，我希望上传简历 PDF，使系统自动构建我的档案，无需手动录入数据。
> 验收标准：PDF/DOCX → AI 解析 → 显示结构化档案 → 一键保存。

**US-02** — 作为新用户，我希望在 UI 中输入 Gemini API Key，使应用无需编辑配置文件即可使用。
> 验收标准：设置页面验证密钥，持久化到 .env，显示状态指示器。


### 史诗2：每日职位发现

**US-10** — 作为求职者，我希望应用每天早上自动抓取招聘网站，无需手动操作即可看到最新职位。
> 验收标准：APScheduler 在配置的时间运行；抓取 Seek、Indeed、LinkedIn；存储结果。

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

| 层级 | 技术 | 版本 | 选型理由 |
|---|---|---|---|
| 前端框架 | React | 18.3 | 生态系统完善，SPA 能力强 |
| 前端构建 | Vite | 5.3 | 快速 HMR 开发体验 |
| 前端样式 | Tailwind CSS | 3.4 | 实用优先，快速构建 UI |
| 前端 HTTP | Axios | 1.7 | 基于 Promise，支持拦截器 |
| 前端路由 | React Router | 6.23 | 文件路由 |
| 后端框架 | FastAPI | 0.134 | 异步，自动生成 OpenAPI 文档 |
| 后端服务器 | Uvicorn | 0.41 | ASGI，生产就绪 |
| ORM | SQLModel | 0.0.22 | SQLAlchemy + Pydantic 混合 |
| 数据库 | SQLite | — | 零配置，可移植 |
| AI 提供商 | Google Gemini 2.5 Flash | — | 结构化输出，响应快 |
| 网页抓取 | Playwright | 1.40 | 无头 Chromium，抗反爬机制 |
| 调度器 | APScheduler | 3.10 | 进程内类 Cron 调度 |
| PDF 解析 | pypdf | 4.0 | 纯 Python，无原生依赖 |
| DOCX 解析 | python-docx | 1.1 | 纯 Python |
| HTTP 客户端 | httpx | 0.27 | 异步，用于 Webhook |
| 时区 | pytz | 2024 | 调度器使用 AEDT 时区 |

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
│   ├── seek.py        — Seek.com.au Playwright 抓取器
│   ├── indeed.py      — Indeed.com.au Playwright 抓取器
│   ├── linkedin.py    — LinkedIn URL 模式抓取器 + RSS feed 解析
│   └── scheduler.py   — 编排器：运行所有抓取器 → 评分 → 通知
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

| 方式 | 封号风险 | 说明 |
|---|---|---|
| 自动登录搜索（已移除） | ⚠️ 高 | 频繁搜索+翻页触发行为检测，不采用 |
| URL 批量解析（F-04） | 🟡 中 | 用户手动提供 URL，系统定向抓取详情 |
| RSS 无登录搜索（F-04b） | 🟢 低 | 访问公开 RSS feed，无需登录，覆盖率有限 |

**设计原则**：LinkedIn 仅作为**定向解析**来源，主力搜索依赖 Seek 和 Indeed。用户在 LinkedIn 发现感兴趣的职位后，手动提交 URL 由系统解析。

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
    source: str                 # "seek" | "indeed" | "linkedin" | "manual"
    raw_jd: str                 # 完整原始职位描述文本
    title: str                  # 解析后的职位名称
    company: str                # 公司名称
    location: str               # 职位地点
    salary_range: str           # 薪资范围（原始字符串，可能为空）
    skills_required: list[str]  # 职位描述中所需技能的 JSON 列表
    match_score: float          # 0.0–1.0（AI 评分）
    gap_analysis: dict          # { strong_matches, missing_skills, notes }
    source_url: str             # 原始职位发布 URL
    status: JobStatus           # 枚举（见下方）
    notification_sent: bool     # 是否已发送推送通知
    created_at: datetime
    updated_at: datetime
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

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `status` | string | — | 按 JobStatus 筛选 |
| `min_score` | float | — | 最低匹配评分 |

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

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/profile` | 获取当前用户档案 |
| PUT | `/api/profile` | 保存完整用户档案 |
| POST | `/api/profile/upload-resume` | 上传简历文件并解析 |
| POST | `/api/profile/parse-resume` | 解析粘贴的简历文本 |

### 6.4 抓取器 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/scrapers/seek` | 启动 Seek 后台抓取任务 |
| POST | `/api/scrapers/indeed` | 启动 Indeed 后台抓取任务 |
| POST | `/api/scrapers/linkedin` | 启动 LinkedIn 自动搜索 |
| POST | `/api/scrapers/linkedin-urls` | 处理 LinkedIn 职位 URL 列表 |
| GET | `/api/tasks/{task_id}` | 轮询后台任务状态 |

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
  "by_source": { "seek": 60, "indeed": 40, "linkedin": 38, "manual": 4 },
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
  "high_score_threshold": 0.80,
  "mid_score_threshold": 0.70,
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

| 设计变量 | 值 |
|---|---|
| 主色调 | Indigo-600 |
| 侧边栏背景 | Gray-900 |
| 卡片背景 | White |
| 边框颜色 | Gray-200 |
| 高分颜色 | Green-600 |
| 中分颜色 | Yellow-600 |
| 低分颜色 | Red-600 |
| 状态标签 | 按状态色彩编码 |
| 字体 | 系统默认（无衬线） |

### 7.3 响应式策略

当前实现面向桌面端（1280px+）。v2.0 未实现移动端响应式布局，计划在 v2.1 更新中实现侧边栏折叠为图标的窄视口方案。

---

## 8. 非功能性需求

### 8.1 性能

| 指标 | 目标 | 备注 |
|---|---|---|
| AI Agent 响应（Scout） | < 10秒/职位 | Gemini 2.5 Flash 延迟 |
| AI Agent 响应（定制） | < 15秒 | 处理较长上下文 |
| 抓取吞吐量 | 约2-3个职位/分钟 | 含反爬延迟 |
| 每日全量 Scout（50个职位） | < 10分钟 | 后台运行可接受 |
| API 响应（非 AI） | < 500毫秒 | 仅数据库查询 |
| 前端首次加载 | < 3秒 | Vite 打包优化 |

### 8.2 可靠性

- **无需认证**：单用户信任模型，无需登录会话管理
- **优雅降级**：LinkedIn URL 解析失败时 → 跳过 LinkedIn，继续 Seek/Indeed
- **幂等抓取**：基于 URL 去重，防止重复处理
- **错误隔离**：每个抓取器独立运行，一个失败不影响其他

### 8.3 安全性

| 安全关注点 | 缓解措施 |
|---|---|
| API Key 存储 | 写入 `.env` 文件（不提交到 git） |
| CORS | 开发环境限制为 localhost:5173 和 localhost:8000 |
| 文件上传 | 仅接受 PDF/DOCX/TXT |
| SQL 注入 | SQLModel ORM 参数化查询；无原始 SQL |
| Prompt 注入 | LLM 输入为结构化（仅职位描述文本） |
| 无认证 | 适用于本地/受信任部署；**不适合多用户公开托管** |

### 8.4 可扩展性

**当前范围**：单用户，本地部署。未设计为多租户。

潜在扩展路径（v3.0+）：
- 添加用户认证（JWT）
- 迁移至 PostgreSQL
- 使用 Docker Compose 容器化
- 添加任务队列（Celery + Redis）

### 8.5 可测试性

- 后端测试套件：`backend/tests/` — **106 个测试全部通过**
- 测试命令：`PYTHONPATH=. python3 -m pytest backend/tests/ -v`
- 覆盖范围：Agent、抓取器、路由、数据模型
- 前端：v2.0 无自动化测试（手动测试）

---

## 9. 开发路线图

### v2.0 — 当前版本 ✅

- 完整自动抓取流水线（Seek、Indeed、LinkedIn）
- AI Scout Agent（匹配评分 + 自动过滤）
- 简历解析与定制
- 求职信生成
- 通知系统（Discord，通过 OpenClaw webhook）
- APScheduler 每日自动化
- React 仪表板（共8个页面）
- 106 个通过测试

### v2.1 — 近期改进

| 功能 | 优先级 | 备注 |
|---|---|---|
| 移动端响应式 UI | P1 | 可折叠侧边栏，触控友好 |
| 简历 PDF 导出 | P1 | 从定制简历生成可下载 PDF |
| 职位备注/标签 | P2 | 用户自定义标签 |
| 多简历档案 | P2 | 针对不同职位类型使用不同档案 |
| Seek 自动申请 | P2 | 通过 Playwright 自动化一键 Easy Apply |
| Indeed 自动申请 | P2 | 表单填写自动化 |
| 更好的评分说明 | P1 | Scout Agent 提供更详细的推理 |

### v2.2 — 中期规划

| 功能 | 优先级 | 备注 |
|---|---|---|
| 邮件集成 | P2 | 通过 SMTP 从应用直接发送求职信 |
| 面试准备 | P3 | LLM 生成职位专属面试问题+答案 |
| 公司调研 | P3 | 自动从 LinkedIn/Glassdoor 获取公司信息 |
| 申请日历 | P2 | 申请和跟进的可视化时间轴 |
| 导出 CSV/PDF | P2 | 导出职位列表和统计数据 |
| Glassdoor 抓取器 | P3 | 额外职位来源 |

### v3.0 — 长期愿景

| 功能 | 备注 |
|---|---|
| 多用户支持 | 认证（JWT）、PostgreSQL、用户隔离 |
| 浏览器扩展 | 一键从任意招聘网站快速添加职位 |
| 作品集集成 | 自动将 GitHub 项目关联到技能和经历 |
| 薪资基准 | 从抓取数据对比目标薪资与市场水平 |
| AI 面试教练 | 模拟面试问答与反馈 |
| 云端托管 | Docker Compose + Render/Railway 一键部署 |

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

| 变量名 | 是否必需 | 默认值 | 说明 |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ 必需 | — | Google Gemini API Key |
| `DISCORD_CHANNEL_ID` | 否 | — | Discord 推送频道 ID |
| `HIGH_SCORE_THRESHOLD` | 否 | `0.80` | 即时推送的评分阈值 |
| `MID_SCORE_THRESHOLD` | 否 | `0.70` | 保存职位的最低阈值 |
| `SCHEDULER_ENABLED` | 否 | `false` | 启用每日自动抓取 |
| `SCHEDULER_HOUR` | 否 | `9` | 运行小时（AEDT 时间） |
| `DEFAULT_MAX_JOBS` | 否 | `15` | 每次抓取查询的默认最大职位数 |

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

### 10.5 LinkedIn 职位提交方式

由于不再使用 Cookie 自动搜索，LinkedIn 职位通过以下两种方式进入系统：

**方式一：手动提交 URL（F-04）**
1. 在 LinkedIn 搜索页面找到感兴趣的职位
2. 复制职位页面 URL
3. 在应用抓取器页面粘贴 URL（支持批量）
4. 系统自动抓取职位详情并评分

**方式二：RSS 订阅（F-04b，待开发）**
1. 在应用设置中配置 LinkedIn RSS 关键词和地区
2. 系统定期拉取公开职位 RSS feed
3. 自动解析并评分，无需任何登录凭据

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

| 方案 | 字体匹配 | 实现难度 | 推荐度 |
|---|---|---|---|
| pymupdf 直接覆盖替换 | ❌ 字体会变 | 低 | 不推荐 |
| WeasyPrint HTML → PDF | ✅ 完全可控 | 中 | ⭐⭐⭐⭐ |
| reportlab 从零绘制 | ✅ 完全可控 | 高 | ⭐⭐⭐ |
| FlowCV API（若开放） | ✅ 原生样式 | 低 | ⭐⭐⭐⭐⭐ |

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
  body { font-family: 'Calibri', sans-serif; margin: 40px; color: #333; }
  h1   { font-size: 24px; font-weight: bold; }
  h2   { font-size: 14px; border-bottom: 1px solid #ccc; color: #2E75B6; margin-top: 16px; }
  p    { font-size: 11px; margin: 4px 0; }
  ul   { font-size: 11px; margin: 4px 0 8px 16px; }
  .skill-tag { display: inline-block; background: #f0f0f0;
               padding: 2px 8px; margin: 2px; border-radius: 3px; font-size: 10px; }
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
  <p><strong>{{ edu.degree }}</strong> — {{ edu.institution }} ({{ edu.duration }})</p>
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

| ID | 功能 | 优先级 | 状态 |
|---|---|---|---|
| F-28 | 基于 Tailor Agent 输出自动生成定制 PDF 简历 | P1 | 🔲 待开发 |
| F-29 | 通过 UI 下载定制 PDF 简历 | P1 | 🔲 待开发 |

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

### Scout Agent — 评分 Schema
```json
{
  "match_score": "number (0.0-1.0)",
  "strong_matches": ["string"],
  "missing_skills": ["string"],
  "notes": "string"
}
```

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

| 术语 | 定义 |
|---|---|
| Scout Agent | AI 模块，用于解析职位描述并评估候选人匹配度 |
| Tailor Agent | AI 模块，用于为特定职位重写简历要点 |
| 差距分析 | Scout 输出：strong_matches、missing_skills、notes |
| ATS 评分 | 求职者追踪系统评分：定制简历中涵盖所需技能的百分比 |
| 高分职位 | 匹配度 ≥ HIGH_SCORE_THRESHOLD（默认 80%） |
| 中分职位 | 匹配度介于 MID 和 HIGH 阈值之间（默认 70–80%） |
| 每日 Scout | 完整流水线：抓取所有来源 → 评分所有职位 → 发送通知 |
| LinkedIn RSS | LinkedIn 公开职位的 RSS feed，无需登录即可访问 |
| source_raw | 原始未修改的要点文本；用于定制可追溯性 |
| WeasyPrint | Python 库，将 HTML/CSS 渲染为 PDF；用于生成定制简历 |
| Jinja2 模板 | 简历 HTML 模板引擎；占位符由 Tailor Agent 输出填充 |
| 定制 PDF | 针对特定职位生成的个性化简历 PDF 文件 |

---

*本规格说明书描述了 Jobseeking Agent v2.0 的已实现状态。这是一份活文档——随着功能的新增或修改，请及时更新。*

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
├── agents/parser.py        ✅ 已实现，禁止修改核心逻辑
├── agents/scout.py         ✅ 已实现，禁止修改核心逻辑
├── agents/tailor.py        ✅ 已实现，禁止修改核心逻辑
├── agents/cover_letter.py  ✅ 已实现，禁止修改核心逻辑
├── scrapers/seek.py        ✅ 已实现，禁止修改
├── scrapers/indeed.py      ✅ 已实现，禁止修改
├── scrapers/linkedin.py    ✅ 已实现（URL模式），允许扩展 RSS
├── models/                 ✅ 全部已实现，禁止修改表结构
├── routers/jobs.py         ✅ 已实现，允许新增端点，禁止修改现有端点签名
├── routers/profile.py      ✅ 已实现，禁止修改
├── routers/scrapers.py     ✅ 已实现，禁止修改
├── routers/notifications.py ✅ 已实现，禁止修改
├── routers/settings.py     ✅ 已实现，禁止修改
├── routers/dashboard.py    ✅ 已实现，禁止修改
├── main.py                 ✅ 已实现，只允许注册新 router
├── config.py               ✅ 已实现，允许新增变量，禁止修改现有变量
└── database.py             ✅ 已实现，禁止修改

frontend/src/               ✅ 全部已实现，禁止修改现有页面逻辑
backend/tests/              ✅ 106个测试，禁止删除或修改现有测试

待新建（Agent 的工作范围）：
├── backend/app/pdf_generator.py        🔲 新建
├── backend/app/routers/files.py        🔲 新建
├── backend/app/scrapers/linkedin_rss.py 🔲 新建
├── templates/resume.html               🔲 新建
└── backend/tests/test_pdf_generator.py 🔲 新建
```

---

### D.2 Agent 分工表

| Agent | 职责 | 负责功能 | 工作目录 |
|---|---|---|---|
| **Backend-PDF Agent** | 实现 PDF 生成模块 | F-28、F-29 | `backend/app/` |
| **Backend-RSS Agent** | 实现 LinkedIn RSS 抓取 | F-04b | `backend/app/scrapers/` |
| **Frontend Agent** | 新增 PDF 下载 UI | F-29 前端部分 | `frontend/src/` |
| **Test Agent** | 编写并运行验收测试 | 所有新增功能 | `backend/tests/` |

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

#### D.3.2 Backend-RSS Agent

**任务**：实现 LinkedIn RSS 无登录职位抓取

**需新建的文件**：

`backend/app/scrapers/linkedin_rss.py`

```python
# 实现规格：
# 1. 函数签名：
async def scrape_linkedin_rss(keywords: list[str], location: str, max_results: int = 15) -> list[ScrapedJob]
# 2. RSS URL 格式：
# https://www.linkedin.com/jobs/search?keywords={keyword}&location={location}&f_TPR=r86400&format=rss
# 3. 使用 httpx 异步请求，不使用 Playwright
# 4. 解析 RSS XML，提取 title/company/url/description
# 5. 返回 list[ScrapedJob]（结构见第5.5节）
# 6. 错误处理：请求失败时返回空列表，写入 WARNING 日志
# 7. 不得引入 Playwright 或任何浏览器依赖
```

**需修改的文件**：

- `backend/app/routers/scrapers.py`：新增端点 `POST /api/scrapers/linkedin-rss`，参照现有 seek/indeed 端点模式实现
- `backend/app/scrapers/scheduler.py`：在每日任务中加入 RSS 抓取调用（可选，由调度器配置控制）

**接口契约**：

```
POST /api/scrapers/linkedin-rss
请求体：
{
  "keywords": ["ML Engineer", "AI Engineer"],
  "location": "Sydney, Australia",
  "max_results": 15
}
响应：{ "task_id": "uuid" }
后续通过 GET /api/tasks/{task_id} 轮询
```

**验收命令**：
```bash
# 1. 单元测试
PYTHONPATH=. pytest backend/tests/test_linkedin_rss.py -v

# 2. 实际 RSS 请求测试（需网络）
python -c "
import asyncio
from backend.app.scrapers.linkedin_rss import scrape_linkedin_rss
jobs = asyncio.run(scrape_linkedin_rss(['ML Engineer'], 'Sydney, Australia', 3))
print(f'抓取到 {len(jobs)} 个职位')
assert len(jobs) >= 0  # 网络失败时允许返回空列表
"

# 3. 回归测试
PYTHONPATH=. pytest backend/tests/ -v --tb=short
# 必须保持 106 个测试全部通过
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

`backend/tests/test_linkedin_rss.py`
```python
# 必须覆盖：
# 1. scrape_linkedin_rss() 网络正常时返回 list[ScrapedJob]
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

| 文件/目录 | Backend-PDF | Backend-RSS | Frontend | Test |
|---|---|---|---|---|
| `backend/app/agents/` | 🔴 只读 | 🔴 只读 | 🚫 禁止 | 🔴 只读 |
| `backend/app/models/` | 🔴 只读 | 🔴 只读 | 🚫 禁止 | 🔴 只读 |
| `backend/app/routers/jobs.py` | 🟡 追加 | 🔴 只读 | 🚫 禁止 | 🔴 只读 |
| `backend/app/routers/scrapers.py` | 🔴 只读 | 🟡 追加 | 🚫 禁止 | 🔴 只读 |
| `backend/app/routers/files.py` | 🟢 新建 | 🚫 禁止 | 🚫 禁止 | 🔴 只读 |
| `backend/app/scrapers/linkedin_rss.py` | 🚫 禁止 | 🟢 新建 | 🚫 禁止 | 🔴 只读 |
| `backend/app/pdf_generator.py` | 🟢 新建 | 🚫 禁止 | 🚫 禁止 | 🔴 只读 |
| `backend/app/main.py` | 🟡 追加 | 🟡 追加 | 🚫 禁止 | 🔴 只读 |
| `backend/app/config.py` | 🟡 追加 | 🟡 追加 | 🚫 禁止 | 🔴 只读 |
| `templates/resume.html` | 🟢 新建 | 🚫 禁止 | 🚫 禁止 | 🔴 只读 |
| `frontend/src/pages/Jobs.tsx` | 🚫 禁止 | 🚫 禁止 | 🟡 追加 | 🔴 只读 |
| `frontend/src/` 其余文件 | 🚫 禁止 | 🚫 禁止 | 🔴 只读 | 🔴 只读 |
| `backend/tests/` 现有文件 | 🔴 只读 | 🔴 只读 | 🚫 禁止 | 🔴 只读 |
| `backend/tests/test_pdf_generator.py` | 🚫 禁止 | 🚫 禁止 | 🚫 禁止 | 🟢 新建 |
| `backend/tests/test_linkedin_rss.py` | 🚫 禁止 | 🚫 禁止 | 🚫 禁止 | 🟢 新建 |
| `data/` | 🟡 写入pdf | 🔴 只读 | 🚫 禁止 | 🔴 只读 |

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