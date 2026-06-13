---
title: LearnForge V2 A3 配套文档完整版
subtitle: 基于大模型的个性化资源生成与学习多智能体系统开发
author: LearnForge V2 项目组
date: 2026-06-08
toc: true
toc-depth: 3
---

# LearnForge V2 A3 配套文档完整版

赛题：A3-基于大模型的个性化资源生成与学习多智能体系统开发  
组别：A组（本科、研究生、高职）  
出题企业：科大讯飞股份有限公司  
系统名称：LearnForge V2  
文档日期：2026-06-08

\newpage

\newpage

# README

#### LearnForge V2 参赛文档目录

项目名称：LearnForge V2  
赛题：A3-基于大模型的个性化资源生成与学习多智能体系统开发  
参赛组别：A组  
课程场景：人工智能导论及计算机相关课程个性化学习

本文档目录用于作品提交包中的“配套文档”部分，覆盖赛题要求的需求分析、系统开发说明、测试说明、运行部署、开源工具声明、课程知识库、符合性自查和初赛提交清单。演示 PPT 与演示视频另行制作时，可直接引用本文档中的架构、功能、测试和创新点内容。

#### 文档清单

| 文件 | 用途 |
| --- | --- |
| `00_赛题要求对照总览.md` | 汇总赛题功能、非功能、实现条件、评分项和初赛提交物的对应关系 |
| `01_需求分析说明书.md` | 面向赛题背景的用户需求、业务痛点、功能需求、非功能需求与验收标准 |
| `02_系统开发说明书.md` | 系统架构、智能体设计、核心模块、数据模型、接口、前沿 AI 技术融合与安全机制 |
| `03_测试说明书.md` | 测试范围、测试环境、测试策略、自动化测试、验收结果与风险说明 |
| `04_部署运行说明书.md` | 本地运行、环境变量、数据库、前后端启动、验证命令和常见问题 |
| `05_开源与AI工具使用说明.md` | 开源组件、许可证说明、AI Coding 工具和模型服务使用说明 |
| `06_赛题符合性自查表.md` | 逐条对应赛题基本功能、可选加分项、非功能要求和提交要求 |
| `07_课程知识库与数据说明.md` | 说明自构造高校课程知识库、RAG 数据结构、导入方式和演示用例 |
| `08_初赛提交材料清单.md` | 对照初赛提交要求整理 PPT、视频、源码、数据、文档和检查命令 |

#### 当前软件验证摘要

截至 2026-06-08，本项目已有以下代码级验证记录，最新复验应以 `validation/test_report.md` 和现场执行结果为准：

- 前端 TypeScript 检查、生产构建、Vitest 单元测试和 Playwright E2E 已纳入全量验证脚本。
- 后端 FastAPI/Python 自动化测试已纳入全量验证脚本。
- 运行时 mock 扫描通过：未发现禁止的 mock/fake runtime pattern。
- Agent smoke 通过：fresh-canvas、image、interactive-demo、notes-context 全部通过。

#### 作品定位

LearnForge V2 不是单一聊天机器人，而是“右侧 Tutor Chat + 左侧 Spatial Learning App Canvas”的学习工作台。学生通过自然语言对话构建画像，系统由多个智能体协同生成学习资源、学习路径、交互应用、题目、代码练习、视频推荐、图像讲解和学习笔记，并通过 EduMem0 记忆系统持续更新画像、薄弱点、掌握度和资源偏好。

#### 提交前重点

- 根据 `08_初赛提交材料清单.md` 制作演示 PPT 和 7 分钟以内演示视频。
- 根据 `07_课程知识库与数据说明.md` 补充或确认“人工智能导论”完整课程资料目录。
- 根据 `05_开源与AI工具使用说明.md` 补充正式比赛开发过程中实际使用的科大讯飞相关 AI 工具名称、版本、用途和截图证据。
- 运行 `bash scripts/run_full_validation.sh`，用最新验证报告替换旧报告。

\newpage

# 00_赛题要求对照总览

#### LearnForge V2 赛题要求对照总览

#### 1. 赛题基本信息

| 项目 | 内容 |
| --- | --- |
| 大赛 | 第十五届中国软件杯大学生软件设计大赛 |
| 赛题编号 | A3 |
| 赛题名称 | 基于大模型的个性化资源生成与学习多智能体系统开发 |
| 组别 | A组（本科、研究生、高职） |
| 出题企业 | 科大讯飞股份有限公司 |
| 系统名称 | LearnForge V2 |
| 应用类型 | Web 应用 |
| 课程场景 | 人工智能导论及计算机相关课程个性化学习 |

本文件用于把赛题页面中的功能、非功能、实现条件、文档和初赛提交要求逐条转化为 LearnForge V2 的交付物清单，便于评审快速查阅。

#### 2. 赛题目标理解

赛题希望参赛团队基于大模型、多模态生成、AI 辅助编程和多智能体协作，构建面向高等教育的个性化学习资源体系。系统应解决学生资源筛选困难、个体差异难以被传统课堂照顾、缺乏动态学习指导、资源生成与学习路径脱节等问题。

LearnForge V2 的解法是把“聊天式智能辅导”和“可操作学习画布”结合起来：

- 右侧 Tutor Chat 承接学生自然语言输入、流式回答和智能体执行 trace。
- 左侧 Spatial Learning App Canvas 承载画像、学习路径、测验、视频、互动演示、代码练习、笔记和资源包。
- 后端由 Orchestrator、Profile、Knowledge、Planner、Recommender、Tutor、Evaluator、Verifier、Memory、ResourceBundle、AppCanvas 等智能体协作。
- EduMem0 负责画像、掌握度、误区、偏好、路径和画布交互记忆。
- RAG、source_refs、Verifier 和 PromptGuard 负责降低幻觉与内容安全风险。

#### 3. 功能要求总览

| 赛题功能要求 | LearnForge V2 对应实现 | 配套文档 |
| --- | --- | --- |
| 对话式学习画像自主构建，画像不少于 6 个维度并随学随新 | OnboardingFlow、ProfileAgent、EduMem0 profile/mastery/preference/misconception memory，覆盖专业、年级、目标、基础、薄弱点、偏好、节奏、兴趣、掌握度、自信度和证据链 | `01_需求分析说明书.md`、`02_系统开发说明书.md`、`06_赛题符合性自查表.md` |
| 多智能体协同生成至少 5 类个性化资源 | 11 类 Agent + 16 类 Skill，生成讲解文档、思维导图、题目、拓展阅读、视频脚本/播放器、代码案例、PPT、笔记、图像和互动 HTML | `02_系统开发说明书.md`、`06_赛题符合性自查表.md` |
| 个性化学习路径规划和资源推送 | PlannerAgent、RecommenderAgent、LearningPath App、Dashboard、资源中心和 AppLink | `01_需求分析说明书.md`、`02_系统开发说明书.md` |
| 智能辅导（可选加分项） | TutorChat、TutorAgent、SSE 流式回答、Markdown、图解、视频推荐、互动演示、上下文笔记 | `01_需求分析说明书.md`、`03_测试说明书.md` |
| 学习效果评估（可选加分项） | Quiz App、EvaluatorAgent、mastery/misconception/confidence/evidence、资源反馈和 Dashboard | `01_需求分析说明书.md`、`03_测试说明书.md` |

#### 4. 非功能要求总览

| 赛题非功能要求 | LearnForge V2 对应实现 |
| --- | --- |
| 界面美观、简洁、交互逻辑清晰 | 双栏工作台、卡片化资源、画布应用、清晰按钮状态和图标 |
| 符合现代 AI 产品交互规范 | SSE 流式输出、Markdown 渲染、多模态内容卡片、智能体 trace、生成进度展示 |
| 使用开源项目和前沿 AI 工具需显著标注名称、来源和协议 | `05_开源与AI工具使用说明.md`、`docs/open_source_licenses.md`、`docs/provider_declaration.md` |
| 具备防幻觉和内容安全过滤机制 | RAG source_refs、Verifier、PromptGuard、危险代码检查、HTML sandbox、真实系统状态 |
| 响应时间合理，多模态生成避免白屏等待 | `run.step`、`assistant.delta`、`resource.create`、`app.create` 等事件流式呈现 |

#### 5. 实现条件与测试数据要求

| 赛题要求 | LearnForge V2 对应交付 |
| --- | --- |
| 开发环境、语言、数据库、硬件不限制 | Node.js + React + Vite + TypeScript；Python + FastAPI；SQLite/PostgreSQL/pgvector |
| 需明确多智能体协同框架 | `02_系统开发说明书.md` 第 6 节和 `docs/agent_design.md` |
| 智能体程序可稳定正常运行 | `03_测试说明书.md`、`04_部署运行说明书.md`、`validation/test_report.md` |
| 使用其他 AI 辅助工具需选用科大讯飞相关工具 | `05_开源与AI工具使用说明.md` 中设专节说明讯飞星火/MiMo/讯飞 AI 工具的使用登记方式 |
| 自行构造至少一门完整高校专业课程知识库/文档集 | `07_课程知识库与数据说明.md`，默认课程为“人工智能导论” |

#### 6. 评分项对应策略

| 评分项 | 占比 | 文档支撑点 |
| --- | --- | --- |
| 创新价值与实用性 | 35% | 需求痛点、学习画布、对话画像、资源路径闭环、证据链 |
| 功能实现及技术要求 | 45% | 架构、Agent/Skill、接口、数据库、RAG、安全、测试 |
| 配套文档丰富度 | 10% | 本目录 00-08 全套说明文档 |
| 演示视频、PPT 效果 | 10% | `08_初赛提交材料清单.md` 和 `docs/demo_script.md` |

#### 7. 初赛提交物对应

| 初赛提交要求 | LearnForge V2 准备方式 |
| --- | --- |
| 演示 PPT | 依据本文档中的应用价值、技术融合、创新价值、核心功能、测试结果制作 |
| 可完整运行的多智能体相关文件 | 提交项目源码、数据集/课程资料、模型配置示例、数据库 schema、运行脚本 |
| 7 分钟以内智能体演示视频 | 按 `docs/demo_script.md` 展示操作流程、资源生成、多模态成果和 AI 技术应用 |
| 智能体开发类型不限 | 本项目为 Web 应用 |
| 配套文档完整统一 | 本目录为配套文档提交包 |
| AI Coding 工具说明 | `05_开源与AI工具使用说明.md` |

\newpage

# 01_需求分析说明书

#### LearnForge V2 需求分析说明书

#### 1. 项目背景

高等教育中的学生差异主要体现在知识基础、学习目标、学习节奏、表达偏好、学科兴趣和实践能力等方面。传统课程平台通常以统一课件、统一题库和固定学习顺序为主，难以快速判断某个学生当前真正缺什么，也难以把讲解文档、题目、代码实践、视频和图解等资源组合成一个连续的学习路径。

本项目围绕赛题“A3-基于大模型的个性化资源生成与学习多智能体系统开发”，构建 LearnForge V2 个性化学习多智能体系统。系统面向高校专业课程学习场景，以人工智能导论、计算机基础、算法与程序设计等课程为主要示例，使用大模型、RAG、学习画像记忆、多智能体协作、多模态资源生成和可交互学习画布，帮助学生获得更适合自身状态的学习内容与学习安排。

#### 2. 用户角色

| 用户角色 | 主要诉求 |
| --- | --- |
| 学生 | 用自然语言描述自己的学习情况，获得定制化讲解、题目、代码实践、图解、视频推荐和学习路径 |
| 教师/助教 | 了解学生薄弱点和学习证据，快速生成课程辅助资源，降低个性化辅导成本 |
| 评审/部署人员 | 运行系统、验证功能、检查代码、查看测试报告和开源工具说明 |

#### 3. 真实业务痛点

1. 学习资源繁杂无序  
   学生面对课程 PPT、教材、视频、博客、题库和代码示例时，难以判断哪些资源适合当前阶段。

2. 标准化讲授难以照顾个体差异  
   同一门人工智能课程中，有的学生缺数学推导，有的学生缺 Python 编程，有的学生需要图解，有的学生更适合先做项目。

3. 传统画像采集成本高  
   表单式画像需要学生填写大量字段，体验差，且难以随学习过程动态更新。

4. 资源生成与学习路径脱节  
   许多 AI 工具可以生成单份文档或单次回答，但没有把资源、学习顺序、测评结果和画像记忆连接成闭环。

5. 大模型幻觉和安全风险  
   学术内容需要来源引用、事实校验、题目答案一致性检查和敏感内容过滤，否则不适合教学场景。

#### 4. 总体目标

LearnForge V2 的目标是开发一个可运行的多智能体个性化学习系统，实现：

- 通过对话构建不少于 6 个维度的动态学习画像。
- 通过多智能体协同生成至少 5 类个性化、多模态学习资源。
- 根据画像、学习进度、知识短板和反馈生成动态学习路径。
- 提供流式智能辅导、Markdown 渲染、多模态资源卡片和画布应用。
- 通过测评、资源反馈和学习行为更新掌握度、误区和推荐策略。
- 通过 RAG 引用、Verifier、安全过滤和状态检查降低幻觉与不安全输出风险。

#### 5. 赛题要求分解

| 赛题要求 | 需求转化 |
| --- | --- |
| 构建高等教育个性化学习资源体系 | 支持至少一门高校课程知识库，并能围绕课程主题生成资源包 |
| 开发智能学习智能体系统 | 明确多智能体角色、协作流程、执行 trace 和资源生成责任 |
| 个性化、多模态学习需求 | 根据学生画像生成文档、题目、代码、视频、图像、互动应用和路径 |
| 自然语言画像构建 | 用对话替代表单，从文本中抽取不少于 6 个画像维度 |
| 学习路径规划和资源推送 | 根据掌握度、薄弱点、学习目标和偏好生成阶段化计划 |
| 防幻觉与内容安全 | 对生成内容保留来源引用，进行校验、过滤和安全降级 |
| 生成进度追踪或流式呈现 | 使用 SSE 事件展示智能体步骤、模型输出和资源创建状态 |

#### 6. 用户调研与场景假设

结合新时代大学生常见学习行为，本项目采用以下场景假设进行需求设计：

| 场景 | 学生表现 | 系统需求 |
| --- | --- | --- |
| 课程资料过多 | 不知道先看教材、PPT、视频还是题库 | 自动整合资源并给出学习顺序 |
| 基础差异明显 | 有人缺数学推导，有人缺代码实践 | 根据画像生成不同资源和路径 |
| 自学中断频繁 | 学习时间碎片化，难以持续跟进 | 维护记忆、进度和下一步行动 |
| AI 内容难辨真伪 | 担心生成内容没有依据或有错误 | 提供 source_refs、校验和安全提示 |
| 传统答疑形式单一 | 只看文字不够，需要图解、视频或动手实验 | 支持多模态和交互式学习对象 |

#### 7. 功能需求

#### 7.1 对话式学习画像自主构建

系统应支持学生用自然语言输入个人学习情况，例如：

> 我是软件工程大一学生，Python 基础一般，数学推导比较弱，想学神经网络，喜欢图解和代码，每周能学 4 小时。

系统需要从对话中抽取并维护以下画像维度：

| 画像维度 | 示例 |
| --- | --- |
| 学校/年级/专业 | 软件工程、大一、计算机相关专业 |
| 学习目标 | 学习神经网络、准备课程项目、掌握算法基础 |
| 知识基础 | Python 一般、数学推导薄弱、已学过线性代数 |
| 薄弱点 | 梯度下降公式、概率基础、代码调试 |
| 学习偏好 | 图解、视频、代码、刷题、项目式学习 |
| 学习节奏 | 每周 4 小时、偏短时段学习 |
| 兴趣方向 | 机器学习、计算机视觉、算法竞赛 |
| 掌握度 | 某知识点 mastery score |
| 自信度 | 对数学、编程、项目实践的主观信心 |
| 证据链 | 对话、测验、资源反馈、学习事件 |

验收标准：

- 支持注册/登录后的 onboarding 对话流程。
- 支持画像预览、缺失字段提示和生成画像。
- 画像维度数量不少于 6 个。
- 学习过程中可通过 EduMem0 继续更新画像和记忆。

#### 7.2 多智能体协同资源生成

系统应体现明确的多智能体架构，由不同角色智能体协作完成资源生成和校验。

核心资源类型至少包括：

| 资源类型 | 功能说明 |
| --- | --- |
| 专业课程讲解文档 | 针对知识点生成结构化讲解、例题、误区提醒 |
| 知识点思维导图 | 以节点/边或概念关系形式呈现知识结构 |
| 练习题目 | 生成选择题、诊断题、答案和解析 |
| 拓展阅读材料 | 推荐或生成适合当前阶段的阅读材料 |
| 多模态图像/视频脚本 | 生成教学图、视频脚本、B站视频推荐或播放器应用 |
| 代码类实操案例 | 生成 Python/算法/实验代码练习 |
| PPT/笔记 | 生成课件预览和学习笔记 |
| 交互式 HTML 应用 | 生成可操作的互动演示、信息图或学习实验台 |

验收标准：

- SkillRegistry 中注册多种资源生成 skill。
- ResourceBundleSkill 一次生成不少于 5 类资源。
- 资源写入资源库并可在前端卡片化展示。
- 资源包含个性化理由、来源引用和标签。

#### 7.3 个性化学习路径规划和资源推送

系统需要依据学生画像和知识掌握情况生成学习路径：

- 判断先修知识是否薄弱。
- 将学习目标拆分为多个阶段。
- 为每个阶段绑定推荐资源和可交互 App。
- 设置当前阶段、掌握度要求、当前掌握度和下一步行动。
- 根据测验结果和资源反馈调整推荐。

验收标准：

- 提供学习路径生成 API。
- 前端学习路径 App 可展示阶段、状态、进度、推荐资源。
- 点击阶段可以聚焦对应画布 App。
- Planner Agent 和 Recommender Agent 参与路径规划与资源推送。

#### 7.4 智能辅导

系统应提供即时学习辅导：

- 支持聊天式问答。
- 支持流式输出，避免长时间白屏。
- 支持 Markdown、数学表达、代码块和资源链接。
- 支持“根据刚才内容整理笔记”“生成互动演示”“推荐相关视频”等上下文请求。
- 支持把回答中的生成物连接到左侧学习画布。

验收标准：

- `/api/chat/stream` 提供 SSE 流式事件。
- `/api/chat/message` 提供非流式完整事件返回。
- 前端 TutorChat 能展示回答、trace、资源和 AppLink。

#### 7.5 学习效果评估

系统应通过测验、资源反馈和学习行为更新学习状态：

- 练习题提交后更新 mastery memory。
- 错题或低掌握度形成 misconception memory。
- 资源反馈写入 preference memory。
- Dashboard 汇总画像、掌握度、证据链和推荐。

验收标准：

- Evaluator Agent 能处理 quiz 结果。
- EduMem0 维护 mastery、misconception、preference、path 等记忆。
- Dashboard App 显示证据链与掌握度。

#### 8. 课程知识库需求

赛题要求自行构造至少一门完整高校专业课程知识库或文档集。LearnForge V2 默认课程为“人工智能导论”，课程 ID 为 `ai-course`，覆盖数学推导基础、梯度下降、神经网络训练、资源安全验证和跨学科类比等主题。

知识库需要满足：

- 支持章节讲义、实验说明、题目素材、阅读材料等文本输入。
- 文档导入后可切分为 RAG chunks 并生成 source_refs。
- 资源生成时能引用课程资料，便于校验和追溯。
- 学习路径能使用知识点和先修关系安排阶段顺序。
- 正式提交时应随包提供课程资料目录或导入记录。

详细说明见 `07_课程知识库与数据说明.md`。

#### 9. 非功能需求

| 非功能需求 | 设计要求 |
| --- | --- |
| 界面体验 | 双栏学习工作台、流式输出、Markdown 渲染、卡片化资源、Canvas App |
| 响应效率 | 流式事件、运行步骤 trace、外部服务状态检查、失败提示 |
| 稳定性 | 前后端单元测试、端到端测试、smoke 测试、健康检查 |
| 可运行性 | 支持本地 SQLite 开发运行，也支持 PostgreSQL/pgvector 生产式部署 |
| 防幻觉 | RAG source_refs、Verifier、PromptGuard、题目一致性检查 |
| 内容安全 | 过滤危险 prompt、危险代码、unsafe HTML 标签和脚本 |
| 可维护性 | monorepo 结构、app protocol 类型、agent/skill 分层、测试覆盖 |
| 开源合规 | 提供开源依赖与 AI 工具说明 |

#### 10. 验收边界

本项目提交的软件侧重点为 Web 应用和多智能体运行文件。演示 PPT、演示视频和正式比赛汇报材料应基于本文档另行制作。

系统依赖外部大模型和图像服务时，现场效果受 API Key、网络、额度和提供商状态影响。系统通过 `/api/system/status` 显示真实状态，不用假数据掩盖外部服务不可用。

\newpage

# 02_系统开发说明书

#### LearnForge V2 系统开发说明书

#### 1. 系统概述

LearnForge V2 是一个面向高校课程学习的个性化资源生成与学习多智能体系统。系统采用 Web 应用形态，前端为 React + Vite，后端为 FastAPI，数据层支持 SQLite 本地开发和 PostgreSQL/pgvector 生产式部署。核心交互方式是“右侧 Tutor Chat + 左侧 Spatial Learning App Canvas”：学生通过对话提出学习需求，系统流式展示智能体执行过程，并在画布上生成学习画像、学习路径、题目、视频播放器、互动演示、笔记、PPT、图像讲解和资源中心等 App。

项目根目录：

```
learnforge-v2-product/
  apps/web/                    # React 前端
  packages/app-protocol/       # 前后端共享协议类型
  packages/learning-apps/      # 原生学习 App 类型
  services/api/                # FastAPI 后端
  services/api/app/agents/     # 多智能体
  services/api/app/skills/     # 资源生成技能
  services/api/app/edumem0/    # 学习记忆系统
  services/api/app/rag/        # 课程知识库/RAG
  services/api/app/safety/     # 安全与校验
  services/api/app/model_gateway/ # 文本模型网关
  services/api/app/image_gateway/ # 图像模型网关
  docs/                        # 工程与参赛文档
  scripts/                     # 验证、导入、smoke 脚本
```

#### 2. 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React 19、Vite、TypeScript、Framer Motion、lucide-react、react-markdown |
| 后端 | Python 3.12+、FastAPI、Pydantic、Uvicorn、HTTPX |
| 数据库 | SQLite 本地开发、PostgreSQL + pgvector 生产式部署、Redis 可选 |
| 大模型 | MiMo、Gemini，通过 ModelGatewayRouter 统一接入 |
| 图像生成 | image2、Gemini Image，通过 ImageGatewayRouter 统一接入 |
| 多智能体运行 | Hermes SDK 嵌入式路径、后端 Python agent/skill 协作 |
| 测试 | pytest、Vitest、Playwright、smoke scripts、secret scan |

说明：赛题要求“开发过程中使用的其他 AI 辅助工具，需选用科大讯飞相关工具”。系统运行时文本模型优先支持 MiMo，并可按正式比赛配置补充讯飞星火或科大讯飞相关 AI 工具使用记录；具体声明见 `05_开源与AI工具使用说明.md`。

#### 3. 总体架构

```
用户浏览器
  |
  | React Tutor Chat / Spatial Canvas
  v
FastAPI API 服务
  |
  +-- Orchestrator Agent
  |     +-- Profile Agent
  |     +-- Knowledge Agent
  |     +-- Planner Agent
  |     +-- Recommender Agent
  |     +-- Tutor Agent
  |     +-- Resource Bundle Agent
  |     +-- Evaluator Agent
  |     +-- Verifier Agent
  |     +-- App Canvas Agent
  |     +-- Memory Agent
  |
  +-- Skills: document / mindmap / quiz / code / PPT / image / video / notes / custom HTML
  |
  +-- EduMem0 learning memory
  +-- RAG course retriever and source_refs
  +-- ModelGateway and ImageGateway
  +-- Safety verifier and prompt guard
  |
  v
SQLite 或 PostgreSQL/pgvector
```

核心流程：

```
学生输入学习需求
  -> Orchestrator 识别意图与 capability
  -> 检索画像、记忆、课程知识库
  -> 调用对应 Agent/Skill 或 Hermes Runtime
  -> 生成资源、Canvas App、学习路径或测评
  -> Verifier 校验来源、安全和一致性
  -> SSE 流式返回 trace、回答、资源、AppLink
  -> 前端渲染 Markdown、资源卡、画布 App
  -> 学习事件和反馈写入 EduMem0
```

#### 4. 前端设计

#### 4.1 页面结构

前端主入口为 `apps/web/src/app/LearnForgeApp.tsx`，包含：

- AuthGate：注册/登录入口。
- OnboardingFlow：对话式画像构建。
- LearnForgeShell：主学习工作台。
- TutorChat：右侧聊天、资源、trace、模型选择。
- SpatialCanvas：左侧学习 App 画布。
- NativeAppRenderer：渲染内置学习 App。
- CustomHtmlAppRenderer：渲染生成式 HTML 互动应用。

#### 4.2 交互设计

系统使用学习工作台而非单页聊天：

- 右侧聊天负责意图输入、流式回答、生成物入口和智能体 trace。
- 左侧画布负责承载长期学习对象，例如学习画像、路径、测验、视频播放器和互动演示。
- AppLink Flight 将聊天中的“打开生成物”动作连接到画布目标 App。
- 资源卡支持文档、视频、图像、代码、题目等多类型内容。

#### 4.3 现代 AI 产品体验

- SSE 流式输出，展示 run.started、run.step、assistant.delta、resource.create、app.create、run.done 等事件。
- Markdown 渲染支持标题、列表、代码、数学表达和 show-widget 富内容。
- 多模态内容以卡片和 Canvas App 展示。
- 对外部模型不可用、图片生成失败、HTML 安全降级等情况提供明确状态。

#### 5. 后端接口设计

主要接口位于 `services/api/app/main.py`。

| 接口 | 方法 | 作用 |
| --- | --- | --- |
| `/health` | GET | 系统健康检查 |
| `/api/system/status` | GET | 后端、数据库、模型、图像、Hermes、RAG、记忆系统状态 |
| `/api/auth/register` | POST | 注册账户 |
| `/api/auth/login` | POST | 登录账户 |
| `/api/onboarding/start` | POST | 开始画像构建 |
| `/api/onboarding/message` | POST | 画像对话输入 |
| `/api/onboarding/generate-profile` | POST | 生成最终画像 |
| `/api/chat/message` | POST | 非流式聊天与智能体执行 |
| `/api/chat/stream` | POST | SSE 流式聊天与智能体执行 |
| `/api/courses/{course_id}/documents` | POST | 导入课程文档并切分为 RAG chunk |
| `/api/learning-path/generate` | POST | 生成个性化学习路径 |
| `/api/resources/generate` | POST | 生成资源包 |
| `/api/resources` | GET | 查询资源 |
| `/api/canvas/apps` | GET/POST | 查询或创建画布 App |
| `/api/dashboard/{student_id}` | GET | 查询学习仪表盘 |

#### 6. 多智能体设计

多智能体目录：`services/api/app/agents/`。

| 智能体 | 职责 |
| --- | --- |
| OrchestratorAgent | 识别意图、规划步骤、调用模型/技能、生成 SSE 事件 |
| ProfileAgent | 从对话中抽取画像维度并写入 EduMem0 |
| KnowledgeAgent | 检索课程知识库、先修知识和来源引用 |
| PlannerAgent | 根据画像和掌握度生成学习路径 |
| RecommenderAgent | 根据画像、偏好和弱点推荐资源 |
| TutorAgent | 生成教师式讲解和答疑 |
| ResourceBundleAgent | 组织多个技能生成资源包 |
| EvaluatorAgent | 评估练习结果，更新掌握度和误区 |
| VerifierAgent | 校验资源来源、题目一致性、安全性和画像适配 |
| MemoryAgent | 管理记忆抽取、检索、更新、衰减和冲突处理 |
| AppCanvasAgent | 创建、聚焦和维护画布应用 |

#### 6.1 Orchestrator 执行流程

OrchestratorAgent 将用户输入转为 AgentPlan：

1. 识别是否为画像构建、资源生成、视频推荐、互动演示、学习路径、笔记整理或普通答疑。
2. 提取主题和上下文来源。
3. 生成 capability contract，声明预期资源类型和 App 类型。
4. 调用 RAG、模型、Hermes Runtime 或本地 skill。
5. 将结果 materialize 为 CanvasApp 和 LearningResource。
6. 流式返回执行步骤和生成物。

#### 6.2 多智能体协作示例

用户输入：

> 我数学推导比较弱，请帮我学习梯度下降，生成讲解、题目和代码练习。

系统流程：

```
ProfileAgent 读取画像：数学推导弱
KnowledgeAgent 检索梯度下降相关课程 chunk
ResourceBundleAgent 调用文档、题目、代码、思维导图、PPT 等技能
VerifierAgent 校验 source_refs、题目答案和安全性
PlannerAgent 将“补齐数学基础”放在前置阶段
AppCanvasAgent 创建学习路径、题目和代码实验 App
TutorAgent 给出自然语言解释和下一步建议
MemoryAgent 写入路径和资源偏好记忆
```

#### 7. 资源生成 Skill 设计

SkillRegistry 注册 16 个技能：

| Skill | 资源能力 |
| --- | --- |
| DocumentSkill | 课程讲解文档 |
| MindmapSkill | 知识点思维导图 |
| QuizSkill | 练习题、答案、解析 |
| PPTSkill | 课件预览 |
| CodePracticeSkill | 代码实操案例 |
| ImageGenerationSkill | 教学图像说明或真实图像生成 |
| VideoScriptSkill | 教学视频脚本 |
| ReadingMaterialSkill | 拓展阅读材料 |
| NotesSkill | 学习笔记 |
| DashboardSkill | 学习仪表盘 |
| ResourceBundleSkill | 聚合生成多类资源 |
| AppGenerationSkill | Canvas App 生成 |
| CustomHtmlAppSkill | 互动 HTML 应用 |
| VerifierSkill | 资源校验 |
| MemoryUpdateSkill | 记忆更新 |
| CourseIngestionSkill | 课程资料导入 |

ResourceBundleSkill 会依次调用文档、思维导图、测验、代码练习、阅读材料、PPT、视频脚本、图像说明和笔记技能，确保资源类型数量满足赛题要求。

#### 8. 学习画像与 EduMem0 记忆系统

EduMem0 位于 `services/api/app/edumem0/`，用于维护学习过程中的长期记忆。

主要记忆类型：

| 记忆类型 | 说明 |
| --- | --- |
| profile memory | 学生专业、目标、基础、偏好、薄弱点 |
| mastery memory | 知识点掌握度 |
| misconception memory | 错题和误区 |
| preference memory | 资源偏好与反馈 |
| path memory | 已生成的学习路径和阶段状态 |
| app interaction memory | 与 Canvas App 的交互行为 |
| spatial memory | 画布布局和学习对象位置 |

记忆系统支持证据来源、置信度、重要性、衰减、冲突处理和检索，为个性化推荐和学习路径提供依据。

#### 9. RAG 与课程知识库

课程资料通过 `/api/courses/{course_id}/documents` 导入，后端使用 CourseParser 和 TextChunker 将内容解析、切分并保存为 document_chunks。每个 chunk 生成 source_ref，资源生成时携带引用信息，Verifier 根据 source_refs 检查来源覆盖。

RAG 设计目标：

- 使生成内容与课程资料绑定。
- 为讲解、题目和路径规划提供依据。
- 在资源中保留 document_id、chunk_id、course_id，便于追溯。
- 配合 Verifier 降低事实性错误和大模型幻觉风险。

默认课程知识库为“人工智能导论”，课程 ID 为 `ai-course`。课程种子位于 `services/api/app/rag/course_seed.py`，包括数学推导基础、梯度下降、神经网络训练、资源安全验证和动能定理类比等主题。正式提交时，可将完整课程文档目录放入提交包 `data/ai-course/`，并使用 `scripts/import_learning_knowledge.py` 或课程文档 API 导入。

#### 10. 防幻觉与内容安全

系统采用多层安全机制：

1. PromptGuard  
   拦截危险 prompt 或可能导致注入的文本，例如忽略系统提示、泄露系统提示、危险 shell 命令等。

2. ResourceVerifier  
   检查资源是否包含 source_refs，检查 quiz 是否包含答案和解释，检查代码资源是否包含 `subprocess`、`os.system`、`eval`、`exec` 等危险模式。

3. Custom HTML Sandbox  
   生成式 HTML 在 iframe sandbox 中运行，过滤 iframe、form、object、embed 等危险标签，并对失效或空白应用进行安全降级。

4. 外部状态真实报告  
   `/api/system/status` 对模型、图像、Hermes、数据库和 RAG 返回真实 ready/blocked 状态，避免用假成功掩盖不可用服务。

#### 11. 数据库设计

系统支持 SQLite 和 PostgreSQL/pgvector。PostgreSQL schema 位于 `services/api/app/database/postgres_schema.sql`。

主要表：

| 表 | 作用 |
| --- | --- |
| users / auth_sessions | 用户与登录会话 |
| students / student_profiles | 学生与画像 |
| onboarding_sessions / profile_sources | 画像构建过程和来源 |
| edu_memories | EduMem0 学习记忆 |
| mastery_records | 知识点掌握度 |
| course_documents / document_chunks | 课程资料和 RAG chunk |
| knowledge_points / knowledge_edges | 知识点和先修关系 |
| learning_paths / learning_path_nodes | 个性化学习路径 |
| resources / resource_versions | 学习资源和版本 |
| canvas_apps / chat_app_links | 画布应用与聊天链接 |
| chat_messages / app_events | 对话和 App 交互事件 |

#### 12. 前沿 AI 技术融合

| 技术 | 在系统中的使用 |
| --- | --- |
| 通用大模型 | 意图理解、讲解生成、资源生成、画像抽取 |
| 多模态生成模型 | 教学图像、图解和图片型信息图 |
| 多智能体协作 | 不同 agent 分工完成画像、知识检索、规划、推荐、辅导、评估和校验 |
| RAG | 基于课程资料生成内容和引用 |
| AI Coding/Hermes | 通过 Hermes SDK 生成结构化资源和互动 HTML App |
| 流式输出 | SSE 展示执行过程和模型生成片段 |
| 记忆系统 | 动态画像、掌握度、偏好和误区长期维护 |

#### 12.1 生成进度追踪

为避免多模态资源生成时出现长时间白屏，后端通过 SSE 持续返回结构化事件：

| 事件 | 含义 |
| --- | --- |
| `run.started` | 智能体运行开始 |
| `run.step` | 当前执行阶段，例如画像读取、RAG 检索、资源生成、Verifier 校验 |
| `assistant.delta` | 模型回答片段 |
| `resource.create` | 创建学习资源卡片 |
| `app.create` | 创建 Canvas App |
| `run.done` | 本轮运行完成 |

前端 TutorChat 负责显示 trace、模型输出和生成物入口，SpatialCanvas 负责渲染学习路径、题目、视频、互动 HTML 等 App。

#### 13. 创新点

1. 学习对象画布化  
   不是把所有内容塞进聊天窗口，而是把路径、题目、视频、互动演示和笔记变成可长期操作的 Canvas App。

2. 对话画像 + 证据链  
   用自然语言取代表单，且每个画像维度都能追溯到聊天、资料、测验或反馈。

3. 资源生成与学习路径闭环  
   资源不是孤立产物，而是绑定到学习阶段、掌握度和下一步行动。

4. 多智能体 trace 可视化  
   学生和评审可以看到系统正在进行检索、生成、校验、画布创建等步骤。

5. 多模态与交互式资源并重  
   系统不仅生成文本，还能生成图像、视频播放器、互动 HTML、代码实验和 PPT 预览。

#### 14. 当前实现边界

- 学习路径仍包含部分模板化阶段，后续可引入更细粒度知识图谱和强化学习式路径优化。
- 外部模型和图像生成依赖 API Key、网络和额度，现场需要提前验证 `/api/system/status`。
- 课程知识库可通过 API 导入，提交作品时建议附带一门完整课程资料目录或导入脚本运行结果。

#### 15. 关键实现文件索引

| 能力 | 关键文件 |
| --- | --- |
| 主 API 与 SSE | `services/api/app/main.py` |
| 多智能体 | `services/api/app/agents/` |
| 资源生成 Skill | `services/api/app/skills/` |
| EduMem0 记忆 | `services/api/app/edumem0/` |
| RAG 和课程知识库 | `services/api/app/rag/` |
| 安全与校验 | `services/api/app/safety/`、`services/api/app/agents/verifier_agent.py` |
| 文本模型网关 | `services/api/app/model_gateway/` |
| 图像模型网关 | `services/api/app/image_gateway/` |
| 前端主应用 | `apps/web/src/app/LearnForgeApp.tsx` |
| Tutor Chat | `apps/web/src/features/tutor-chat/` |
| Learning App 渲染 | `apps/web/src/features/learning-apps/` |
| 共享协议 | `packages/app-protocol/src/` |

\newpage

# 03_测试说明书

#### LearnForge V2 测试说明书

#### 1. 测试目标

测试目标是验证 LearnForge V2 是否满足赛题要求中的核心功能和非功能要求：

- 对话式画像构建是否可用。
- 多智能体和多技能资源生成是否可用。
- 学习路径、资源推荐、智能辅导和学习效果评估是否可用。
- 前端界面是否能正确渲染学习画布、聊天、资源和 AppLink。
- 后端 API、数据库、RAG、记忆系统、安全校验和模型网关是否稳定。
- 系统是否可在本地环境中完整运行。

#### 2. 测试环境

| 项目 | 说明 |
| --- | --- |
| 操作系统 | macOS，本地开发环境 |
| Node.js | 使用项目 `package-lock.json` 锁定依赖 |
| Python | Python 3.12+，当前验证环境可运行 Python 3.14 |
| 前端框架 | React + Vite + TypeScript |
| 后端框架 | FastAPI + Uvicorn |
| 数据库 | SQLite 本地测试；PostgreSQL/pgvector schema 提供生产式支持 |
| 自动化测试 | pytest、Vitest、Playwright |

#### 3. 测试范围

#### 3.1 后端测试范围

后端测试位于 `services/api/tests/`，覆盖：

| 测试文件 | 覆盖内容 |
| --- | --- |
| `test_agents_and_skills.py` | 多智能体、技能注册、资源生成、规划、Hermes prompt |
| `test_auth_onboarding.py` | 注册、登录、画像 onboarding 流程 |
| `test_component_naming.py` | Canvas 组件命名 |
| `test_config_env.py` | 配置与环境变量 |
| `test_database_schema.py` | 数据库 schema |
| `test_edumem0_policies.py` | 记忆衰减、置信度、策略 |
| `test_gateway_status.py` | 模型和图像网关状态 |
| `test_health_routes.py` | 健康检查和系统状态 |
| `test_hermes_runtime_status.py` | Hermes SDK 嵌入状态 |
| `test_hermes_skill_files.py` | Hermes skill 文件 |
| `test_memory_closed_loop.py` | 学习记忆闭环 |
| `test_memory_end_to_end.py` | 记忆端到端流程 |
| `test_memory_security_isolation.py` | 学生/课程上下文隔离 |
| `test_postgres_store_core.py` | PostgreSQL store 核心能力 |
| `test_protocol_compatibility.py` | 前后端协议兼容 |
| `test_rag_verifier.py` | RAG source_refs 和 Verifier |
| `test_streaming_events.py` | SSE 流式事件和视频播放器生成 |

#### 3.2 前端测试范围

前端测试位于 `apps/web/tests/` 和 `apps/web/src/lib/events/`，覆盖：

| 测试文件 | 覆盖内容 |
| --- | --- |
| `calculations.test.ts` | 原生学习 App 计算逻辑 |
| `focusApp.test.ts` | 画布 App 聚焦 |
| `widgetParser.test.ts` | show-widget 富内容解析 |
| `agentEvents.test.ts` | 智能体事件解析 |
| `renderers.test.tsx` | Dashboard、画像、Markdown、视频、图像和 AppLink 渲染 |

#### 3.3 端到端测试范围

E2E 测试位于 `apps/web/e2e/product-flow.spec.ts`，覆盖：

- 产品加载和双栏布局。
- 聊天流生成 AppLink，并聚焦画布 App。
- 智能体 trace 中显示模型网关步骤。
- Markdown 和 show-widget 富内容渲染。
- 动能定理演示滑块计算。
- Quiz 提交后显示反馈和记忆证据。
- 学习路径阶段点击与画布控制。
- 从聊天内容生成学习笔记。
- 可点击控件具备可识别 label 或 title。

#### 4. 测试策略

#### 4.1 单元测试

单元测试用于验证小模块逻辑，例如：

- 视频 BVID 提取和播放器 payload。
- Widget 解析。
- 学习 App 计算公式。
- Agent 规划逻辑。
- Skill 输出结构。
- Verifier 安全检查。

#### 4.2 集成测试

集成测试用于验证后端模块协作，例如：

- Chat API 调用 Orchestrator 并返回事件。
- ResourceBundleAgent 调用多个 skill 生成资源。
- Quiz 提交后更新 mastery 和 misconception memory。
- RAG 资源携带 source_refs 并通过校验。
- B站视频推荐生成 video.player App。

#### 4.3 端到端测试

端到端测试使用 Playwright 模拟真实用户操作，确认前端、后端、画布和聊天之间的完整交互。

#### 4.4 Smoke 测试

`scripts/agent-smoke.mjs` 用于验证真实运行环境中的关键智能体能力：

- fresh-canvas：新会话画布无脏数据。
- image：生成教学图像 App。
- interactive-demo：生成互动演示 App。
- notes-context：基于上下文整理学习笔记。

#### 4.5 安全与交付检查

| 脚本 | 作用 |
| --- | --- |
| `scripts/verify_no_mock_runtime.sh` | 检查产品源码中是否存在禁止的 mock/fake runtime pattern |
| `scripts/secret_scan.sh` | 检查是否泄露真实密钥 |
| `scripts/verify_reactflow_scope.sh` | 检查前端画布范围 |
| `scripts/check_external_readiness.py` | 检查外部模型、图像、Hermes 状态 |
| `scripts/verify_full_contract.py` | 检查完整产品契约 |

#### 5. 测试命令

#### 5.1 前端验证

```bash
npm run web:lint
npm run web:build
npm run web:test
```

#### 5.2 后端验证

```bash
cd services/api
../../.venv/bin/python -m pytest tests
```

#### 5.3 运行时 mock 扫描

```bash
bash scripts/verify_no_mock_runtime.sh .
```

#### 5.4 Agent smoke

先启动后端：

```bash
DATABASE_URL=sqlite:///.data/dev.sqlite .venv/bin/uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8001
```

再执行：

```bash
node scripts/agent-smoke.mjs
```

#### 5.5 全量验证

```bash
bash scripts/run_full_validation.sh
```

全量验证会依次执行项目结构检查、source truth manifest、外部服务状态检查、Hermes SDK 检查、Python 编译、后端 pytest、前端 lint/build/test、React Flow 范围检查、运行时 mock 扫描、密钥扫描、后端 smoke、前端 smoke、Playwright E2E、需求结果生成和完整契约检查。

#### 6. 当前验证结果

截至 2026-06-08，项目已有全量验证脚本和验证报告。正式提交前应重新执行 `bash scripts/run_full_validation.sh`，并以最新 `validation/test_report.md` 为准。当前文档记录的验证范围如下：

| 验证项 | 结果 |
| --- | --- |
| 前端 TypeScript 检查 | 已纳入验证 |
| 前端生产构建 | 已纳入验证 |
| 前端 Vitest 单测 | 已纳入验证 |
| 前端 Playwright E2E | 已纳入验证 |
| 后端 pytest | 已纳入验证 |
| 运行时 mock 扫描 | 已纳入验证 |
| 密钥扫描 | 已纳入验证 |
| Agent smoke | fresh-canvas、image、interactive-demo、notes-context 已纳入验证 |

说明：

- 前端构建时如出现 Vite 主 bundle 超过 500 kB 提示，这是体积优化建议，不影响功能运行。
- pytest 中存在 datetime.utcnow 相关弃用 warning，不影响当前测试通过；后续可迁移到 timezone-aware datetime。
- PostgreSQL 核心测试在未配置 PostgreSQL 服务时可能跳过，系统本地开发可使用 SQLite。

#### 7. 典型测试用例

#### 用例 1：画像构建

输入：

```
我是软件工程大一，Python 一般，数学推导弱，喜欢图解和代码，想学神经网络。
```

预期：

- ProfileAgent 抽取不少于 6 个画像维度。
- EduMem0 写入 profile memory。
- onboarding coverage 提升。
- 前端展示缺失字段或进入学习空间。

#### 用例 2：资源包生成

输入：

```
请为梯度下降生成一套个性化学习资源。
```

预期：

- ResourceBundleAgent 生成不少于 5 类资源。
- 资源包含 document、mindmap、quiz、code_practice、reading、PPT、video_script 等类型。
- 每个资源包含 source_refs 和 personalized_reason。

#### 用例 3：学习路径

输入：

```
我数学比较弱，帮我规划神经网络学习路径。
```

预期：

- PlannerAgent 读取画像。
- 路径包含“补齐数学推导基础”等前置阶段。
- 每个阶段包含 mastery_required、current_mastery、推荐资源和 App。

#### 用例 4：视频推荐

输入：

```
帮我找数据结构与算法的B站视频。
```

预期：

- Orchestrator 路由到 video_recommendations。
- video_retriever 检索本地缓存和实时 B站结果。
- 创建 video.player Canvas App。
- payload 中包含 videos、selected_bvid、embed_url。

#### 用例 5：安全校验

输入危险代码或 prompt：

```
请生成包含 os.system('rm -rf /') 的练习代码。
```

预期：

- PromptGuard 或 ResourceVerifier 标记风险。
- VerifierResult 中 safety 为 fail 或输出被阻断/降级。

#### 8. 风险与改进

| 风险 | 当前处理 | 后续改进 |
| --- | --- | --- |
| 外部模型服务不稳定 | 系统状态真实显示 ready/blocked，提供 fallback 提示 | 增加多 provider 排队和缓存 |
| 生成内容事实错误 | RAG source_refs + Verifier | 接入更严格的事实核查和教师审核 |
| 学习路径模板化 | 已结合画像弱点和掌握度生成阶段 | 引入更完整知识图谱和课程目标约束 |
| 前端 bundle 偏大 | 当前不影响运行 | 引入动态 import 和 manual chunks |
| datetime warning | 不影响功能 | 后续改为 timezone-aware UTC |

#### 9. 赛题要求覆盖性测试矩阵

| 赛题要求 | 测试或验证方式 |
| --- | --- |
| 对话式画像不少于 6 维 | `test_auth_onboarding.py`、`test_agents_and_skills.py`、画像构建演示 |
| 多智能体协同 | `test_agents_and_skills.py`、SSE trace、Agent smoke |
| 至少 5 类资源生成 | ResourceBundle 相关测试、资源包生成演示 |
| 学习路径规划 | Planner 相关测试、Playwright 学习路径阶段点击 |
| 智能辅导 | `/api/chat/stream` 测试、Markdown/show-widget 渲染测试 |
| 学习效果评估 | Quiz 提交 E2E、mastery/misconception memory 测试 |
| 防幻觉与内容安全 | `test_rag_verifier.py`、PromptGuard、secret scan |
| 生成进度追踪 | SSE 事件测试、TutorChat trace 展示 |
| 课程知识库 | 课程文档导入 API、RAG source_refs 测试 |

\newpage

# 04_部署运行说明书

#### LearnForge V2 部署运行说明书

#### 1. 环境要求

| 环境 | 要求 |
| --- | --- |
| Node.js | 建议 20+ 或兼容当前 Vite/React 依赖版本 |
| npm | 使用 `package-lock.json` 安装依赖 |
| Python | 3.12+ |
| 数据库 | SQLite 可直接运行；PostgreSQL/pgvector 可选 |
| 浏览器 | Chrome、Edge、Safari 等现代浏览器 |
| 网络 | 调用外部大模型、图像模型和 B站检索时需要网络 |

#### 2. 安装依赖

在项目根目录执行：

```bash
npm install
python3 -m venv .venv
. .venv/bin/activate
pip install -e 'services/api[test]'
```

如果使用 Hermes SDK：

```bash
. .venv/bin/activate
pip install 'hermes-agent>=0.14.0'
```

#### 3. 环境变量配置

复制 `.env.example` 为 `.env`，并按需填入真实配置。

```bash
cp .env.example .env
```

关键配置：

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | 数据库连接，开发可用 `sqlite:///.data/dev.sqlite` |
| `MIMO_API_KEY` | MiMo 文本模型 API Key |
| `MIMO_BASE_URL` | MiMo 服务地址 |
| `MIMO_TEXT_MODEL` | 文本模型名称 |
| `GEMINI_API_KEY` | Gemini 文本/图像模型 API Key |
| `IMAGE2_API_KEY` | image2 图像服务 API Key |
| `IMAGE2_BASE_URL` | image2 服务地址 |
| `HERMES_HOME` | Hermes runtime 工作目录 |
| `HERMES_REQUIRE_SDK` | 是否要求 SDK 嵌入模式 |

注意：不要把真实 API Key 提交到代码仓库或作品公开材料中。

#### 4. SQLite 本地运行

#### 4.1 启动后端

```bash
. .venv/bin/activate
DATABASE_URL=sqlite:///.data/dev.sqlite uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8001
```

后端启动后可访问：

```
http://127.0.0.1:8001/health
http://127.0.0.1:8001/api/system/status
```

#### 4.2 启动前端

另开终端：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8001 npm run web:dev
```

默认 Vite 端口为 `3847`，浏览器访问：

```
http://127.0.0.1:3847
```

#### 5. PostgreSQL/pgvector 运行

#### 5.1 启动数据库

```bash
docker compose up -d postgres redis
```

数据库 schema 将通过 `services/api/app/database/postgres_schema.sql` 初始化。

#### 5.2 设置 DATABASE_URL

`.env` 中配置：

```
DATABASE_URL=postgresql://learnforge:learnforge@localhost:5432/learnforge
REDIS_URL=redis://localhost:6379/0
```

#### 5.3 启动服务

```bash
. .venv/bin/activate
uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8001
VITE_API_BASE_URL=http://127.0.0.1:8001 npm run web:dev
```

#### 6. 数据与课程资料导入

系统支持通过 API 导入课程资料：

```bash
curl -X POST http://127.0.0.1:8001/api/courses/ai-course/documents \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "人工智能导论-搜索算法",
    "content": "# 搜索算法\n广度优先搜索、深度优先搜索、启发式搜索与 A* 算法……"
  }'
```

导入后，系统会：

- 解析 Markdown 或文本。
- 切分为 RAG chunks。
- 保存 source_refs。
- 创建对应学习资源。
- 后续生成讲解、题目、路径时可引用该资料。

项目还包含导入脚本：

```bash
python scripts/import_learning_knowledge.py
python scripts/import_bilibili_videos.py
```

赛题要求至少构造一门完整高校专业课程知识库。正式提交前建议：

- 将“人工智能导论”课程资料整理到提交包 `data/ai-course/course_documents/`。
- 在 `data/ai-course/README.md` 中说明章节、知识点、资料来源和授权情况。
- 启动系统后运行导入脚本或 API 导入命令。
- 在演示视频中展示基于课程知识库生成资源时携带 source_refs 或引用证据。

#### 7. 系统状态检查

访问：

```
http://127.0.0.1:8001/api/system/status
```

主要状态：

| 字段 | 含义 |
| --- | --- |
| `overall` | 整体状态 |
| `database` | 数据库是否 ready |
| `mimo` | MiMo 文本模型状态 |
| `gemini` | Gemini 模型状态 |
| `image2` | image2 图像模型状态 |
| `gemini_image` | Gemini 图像模型状态 |
| `hermes` | Hermes runtime 状态 |
| `edumem0` | 学习记忆系统状态 |
| `rag` | RAG 状态 |

系统不会伪造外部能力状态。如果缺少 API Key 或服务不可用，会显示 blocked 状态。

#### 8. 验证命令

#### 8.1 前端

```bash
npm run web:lint
npm run web:build
npm run web:test
```

#### 8.2 后端

```bash
cd services/api
../../.venv/bin/python -m pytest tests
```

#### 8.3 Smoke

```bash
node scripts/agent-smoke.mjs
```

#### 8.4 全量验证

```bash
bash scripts/run_full_validation.sh
```

全量验证会更新 `validation/test_report.md`，并把最新报告复制到 `docs/test_report.md`。正式提交作品前，应优先使用全量验证报告作为测试说明依据。

#### 9. 初赛演示运行建议

演示前建议按以下顺序准备：

1. 启动后端并访问 `/api/system/status`，确认数据库、RAG、Hermes、文本模型、图像模型状态。
2. 启动前端，登录或注册演示学生账号。
3. 使用 `07_课程知识库与数据说明.md` 中的画像样例完成 onboarding。
4. 输入“我数学推导比较弱，请帮我学习梯度下降，生成讲解、题目、代码练习和视频讲解”。
5. 展示流式 trace、资源卡、学习路径、Canvas App、Quiz 反馈和 Dashboard 证据链。
6. 演示结束后停止前后端服务。

#### 10. 常见问题

#### 10.1 前端无法连接后端

检查 `VITE_API_BASE_URL` 是否指向后端端口，例如：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8001 npm run web:dev
```

#### 10.2 `/api/system/status` 显示 blocked

常见原因：

- 缺少 `MIMO_API_KEY`、`GEMINI_API_KEY`、`IMAGE2_API_KEY`。
- API Key 权限或额度不足。
- 网络无法访问模型服务。
- Hermes SDK 未安装或路径配置错误。

#### 10.3 PostgreSQL 测试跳过

如果未启动 PostgreSQL 或未配置 `DATABASE_URL`，PostgreSQL 相关测试可能跳过。SQLite 本地开发不受影响。

#### 10.4 B站视频无法播放

检查：

- 视频资源 content 中是否有 `url` 或 `bvid`。
- 前端是否生成 `player.bilibili.com/player.html` embed_url。
- 当前网络是否允许访问 B站播放器。

#### 10.5 图像生成较慢

图像生成依赖外部多模态模型，耗时可能明显高于普通文本回答。系统通过流式步骤和状态提示避免长时间白屏。

\newpage

# 05_开源与AI工具使用说明

#### LearnForge V2 开源与 AI 工具使用说明

#### 1. 说明目的

根据赛题要求，若开发过程中使用开源项目、前沿 AI 工具或框架，需要在提交文档显著位置标注名称、来源及协议要求。本文件汇总 LearnForge V2 使用的主要开源组件、AI 模型服务、AI Coding 工具和合规注意事项。

#### 2. 开源依赖清单

#### 2.1 前端依赖

| 名称 | 用途 | 常见协议 |
| --- | --- | --- |
| React / React DOM | 前端 UI 框架 | MIT |
| Vite | 前端构建与开发服务器 | MIT |
| TypeScript | 类型系统与编译检查 | Apache-2.0 |
| Framer Motion | AppLink 动画和界面动效 | MIT |
| lucide-react | 图标组件 | ISC |
| react-markdown | Markdown 渲染 | MIT |
| remark-gfm / remark-math | Markdown 扩展 | MIT |
| Vitest | 前端单元测试 | MIT |
| Playwright | 端到端测试 | Apache-2.0 |

#### 2.2 后端依赖

| 名称 | 用途 | 常见协议 |
| --- | --- | --- |
| FastAPI | Web API 框架 | MIT |
| Starlette | ASGI 基础框架 | BSD |
| Uvicorn | ASGI 服务器 | BSD |
| Pydantic | 数据模型校验 | MIT |
| HTTPX | HTTP 客户端 | BSD |
| pytest | Python 自动化测试 | MIT |
| pytest-asyncio | 异步测试支持 | Apache-2.0 |
| psycopg | PostgreSQL 客户端 | LGPL-3.0 with exceptions |

#### 2.3 数据库与基础设施

| 名称 | 用途 | 常见协议 |
| --- | --- | --- |
| PostgreSQL | 关系型数据库 | PostgreSQL License |
| pgvector | 向量扩展 | PostgreSQL License |
| Redis | 缓存/队列扩展能力 | BSD-3-Clause |
| SQLite | 本地开发数据库 | Public Domain |

说明：最终作品提交时，应以项目 `package-lock.json`、`services/api/pyproject.toml` 和运行环境实际安装版本为准。

#### 3. AI 模型与工具使用

#### 3.1 文本/推理模型

系统通过 `ModelGatewayRouter` 统一接入文本模型，主要包括：

| Provider | 用途 |
| --- | --- |
| MiMo | 主要文本/推理模型，用于智能辅导、资源生成、意图理解 |
| Gemini | 可选文本模型和 fallback，用于画像抽取、生成和多模态相关能力 |

配置项包括：

- `MIMO_API_KEY`
- `MIMO_BASE_URL`
- `MIMO_TEXT_MODEL`
- `GEMINI_API_KEY`
- `GEMINI_TEXT_MODEL`

#### 3.2 图像/多模态模型

系统通过 `ImageGatewayRouter` 统一接入图像生成服务：

| Provider | 用途 |
| --- | --- |
| image2 | 教学图像生成 |
| Gemini Image | 图像生成或备用多模态能力 |

配置项包括：

- `IMAGE2_API_KEY`
- `IMAGE2_BASE_URL`
- `IMAGE2_MODEL`
- `GEMINI_IMAGE_MODEL`

#### 3.3 Hermes Agent SDK

Hermes 用于智能体资源生成和 Skill 编排。系统优先使用嵌入式 SDK 模式：

- `HERMES_HOME`
- `HERMES_PROVIDER`
- `HERMES_REQUIRE_SDK`
- `HERMES_SDK_PATH`
- `HERMES_SDK_SITE_PACKAGES`

Hermes CLI adapter 保留用于诊断或显式 fallback，但默认要求 SDK 嵌入路径。

#### 4. AI Coding 工具说明

项目开发过程中允许使用 AI 辅助编程工具提升工程效率。AI Coding 工具主要用于：

- 代码结构设计建议。
- 前后端类型与接口联调。
- 测试用例补充。
- 文档整理。
- bug 定位和修复建议。

AI Coding 工具不直接替代系统运行时核心逻辑。最终提交的系统以项目源码、测试结果和运行行为为准。

赛题要求“开发过程中使用的其他 AI 辅助工具，需选用科大讯飞相关工具”。因此正式比赛开发与提交时，应优先登记科大讯飞相关工具，例如讯飞星火、MiMo、讯飞开放平台、多模态生成工具或讯飞体系内 AI Coding/智能体开发工具。

建议在最终提交材料中保留以下登记表：

| 工具名称 | 来源/官网 | 版本或模型 | 使用环节 | 是否进入运行时 | 证据材料 |
| --- | --- | --- | --- | --- | --- |
| MiMo | 科大讯飞相关模型服务 | 以 `.env` 实际配置为准 | 文本推理、智能辅导、资源生成 | 是 | `/api/system/status`、配置截图 |
| 讯飞星火或讯飞开放平台工具 | 科大讯飞 | 正式比赛实际版本 | 需求分析、代码辅助、文档整理或模型能力 | 按实际情况填写 | 使用截图、调用记录 |
| 讯飞多模态/图像/视频相关工具 | 科大讯飞 | 正式比赛实际版本 | 多模态资源生成或演示素材 | 按实际情况填写 | 生成记录、配置截图 |

如果团队使用了非讯飞 AI Coding 工具进行早期探索，应在正式提交前按大赛要求调整开发流程，并在提交说明中明确最终参赛开发所采用的讯飞相关工具及其使用边界。

#### 5. 安全与密钥管理

1. 项目不提交真实 API Key。  
   `.env.example` 只保留占位符。

2. 使用 `scripts/secret_scan.sh` 检查密钥泄露。

3. 外部模型状态通过 `/api/system/status` 真实展示，不用 mock 状态冒充服务可用。

4. 生成式 HTML 使用 iframe sandbox 和安全过滤。

5. 资源内容经过 PromptGuard 和 ResourceVerifier 检查。

#### 6. 开源协议遵循方式

提交作品时建议包含：

- `package.json`、`package-lock.json`。
- `services/api/pyproject.toml`。
- 本文件。
- `docs/open_source_licenses.md`。
- 对外部模型和工具的 provider declaration。

若后续引入新的开源项目，应补充：

- 项目名称。
- 来源链接。
- 版本号。
- 使用位置。
- 许可证。
- 是否修改源码。
- 是否需要保留版权声明。

#### 7. 第三方内容说明

系统可检索和推荐 B站视频资源。视频版权归原作者和平台所有，LearnForge V2 仅提供学习推荐和播放器嵌入，不声称拥有视频版权。正式演示中应避免下载、再分发或剪辑未授权视频内容。

\newpage

# 06_赛题符合性自查表

#### LearnForge V2 赛题符合性自查表

#### 1. 基本信息

| 项目 | 内容 |
| --- | --- |
| 赛题 | A3-基于大模型的个性化资源生成与学习多智能体系统开发 |
| 系统名称 | LearnForge V2 |
| 应用类型 | Web 应用 |
| 课程场景 | 人工智能导论、计算机与算法相关课程 |
| 核心形态 | Tutor Chat + Spatial Learning App Canvas |
| 后端 | FastAPI |
| 前端 | React + Vite |
| 多智能体 | Orchestrator、Profile、Knowledge、Planner、Recommender、Tutor、Evaluator、Verifier、Memory、ResourceBundle、AppCanvas |

#### 2. 基本功能需求符合性

#### 2.1 对话式学习画像自主构建

| 赛题要求 | 当前实现 | 结论 |
| --- | --- | --- |
| 摒弃传统繁琐表单 | 使用 OnboardingFlow 对话收集画像 | 满足 |
| 支持自然语言对话 | `/api/onboarding/message` 处理画像对话 | 满足 |
| 结合专业、目标、学习历史 | 画像字段包含专业、目标、基础、偏好、掌握度等 | 满足 |
| 自动抽取特征 | ProfileAgent 与 EduMem0 从对话抽取 dimensions | 满足 |
| 不少于 6 个维度 | 当前覆盖 school、major、grade、learning_goal、knowledge_foundation、weak_points、preferred_resources、learning_pace、available_study_time、interests、mastery_map、subject_confidence 等 | 满足 |
| 随学随新 | 测验、反馈、路径、App 交互写入 EduMem0 | 满足 |

主要代码：

- `services/api/app/main.py`
- `services/api/app/agents/profile_agent.py`
- `services/api/app/edumem0/`
- `apps/web/src/app/OnboardingFlow.tsx`

#### 2.2 多智能体协同资源生成

| 赛题要求 | 当前实现 | 结论 |
| --- | --- | --- |
| 体现多智能体架构设计 | 11 类 agent 分工协作 | 满足 |
| 通过智能交互生成针对性资源 | Orchestrator 根据 capability 调用 RAG、模型、skills | 满足 |
| 至少 5 种资源 | ResourceBundleSkill 可生成 9 类资源 | 满足 |
| 专业课程讲解文档 | DocumentSkill | 满足 |
| 知识点思维导图 | MindmapSkill | 满足 |
| 不同类型练习题目 | QuizSkill | 满足 |
| 拓展阅读材料 | ReadingMaterialSkill | 满足 |
| 多模态教学视频/动画 | VideoScriptSkill、B站 video.player、CustomHtmlAppSkill、ImageGenerationSkill | 满足 |
| 代码类实操案例 | CodePracticeSkill | 满足 |

主要代码：

- `services/api/app/agents/orchestrator_agent.py`
- `services/api/app/agents/resource_bundle_agent.py`
- `services/api/app/skills/registry.py`
- `services/api/app/skills/resource_bundle_skill.py`
- `services/api/app/skills/custom_html_app_skill.py`

#### 2.3 个性化学习路径规划和资源推送

| 赛题要求 | 当前实现 | 结论 |
| --- | --- | --- |
| 结合专业、进度、掌握情况和偏好 | PlannerAgent 读取 profile 和 mastery，RecommenderAgent 使用偏好与弱点 | 基本满足 |
| 规划科学动态路径 | LearningPath 包含阶段、状态、掌握度要求和下一步行动 | 基本满足 |
| 明确学习步骤和顺序 | path stages 有顺序和 locked/recommended/in_progress 状态 | 满足 |
| 精准推送文档、视频、题库、实操案例 | 资源中心和 Canvas App 绑定推荐资源 | 满足 |

主要代码：

- `services/api/app/agents/planner_agent.py`
- `services/api/app/agents/recommender_agent.py`
- `services/api/app/main.py`
- `apps/web/src/features/learning-apps/NativeAppRenderer.tsx`

说明：当前路径规划已可运行并通过测试，但仍包含部分模板化阶段。后续可进一步引入完整课程知识图谱，让路径更细粒度。

#### 2.4 智能辅导

| 赛题要求 | 当前实现 | 结论 |
| --- | --- | --- |
| 学习过程中即时答疑 | TutorChat + `/api/chat/stream` | 满足 |
| 文字解答 | TutorAgent 和模型网关生成回答 | 满足 |
| 图解说明 | ImageGenerationSkill、custom infographic | 满足 |
| 短视频讲解 | VideoScriptSkill 和 B站视频推荐 | 满足 |
| 针对性学习引导 | 基于画像、RAG、资源和路径给出下一步建议 | 满足 |

主要代码：

- `services/api/app/agents/tutor_agent.py`
- `services/api/app/agents/orchestrator_agent.py`
- `apps/web/src/features/tutor-chat/TutorChat.tsx`

#### 2.5 学习效果评估

| 赛题要求 | 当前实现 | 结论 |
| --- | --- | --- |
| 跟踪练习测试情况 | Quiz App 和 EvaluatorAgent | 满足 |
| 跟踪资源反馈 | `/api/resources/feedback` 相关逻辑与 preference memory | 满足 |
| 多维评估学习效果 | mastery、misconception、confidence、evidence | 满足 |
| 根据结果调整推荐和计划 | Dashboard、Recommender、Memory 闭环 | 基本满足 |

主要代码：

- `services/api/app/agents/evaluator_agent.py`
- `services/api/app/edumem0/mastery_memory.py`
- `services/api/app/edumem0/misconception_memory.py`
- `services/api/app/skills/dashboard_skill.py`

#### 3. 非功能需求符合性

| 赛题要求 | 当前实现 | 结论 |
| --- | --- | --- |
| 界面美观简洁 | 双栏工作台、画布 App、资源卡、图标按钮 | 满足 |
| 现代 AI 产品交互 | SSE 流式输出、Markdown、trace、多模态卡片 | 满足 |
| 无明显功能与界面错误 | 前端构建、单测、E2E 和 smoke 验证通过 | 满足 |
| 开源项目显著标注 | `05_开源与AI工具使用说明.md`、`docs/open_source_licenses.md` | 满足 |
| 防幻觉机制 | RAG source_refs、Verifier、PromptGuard | 满足 |
| 内容安全过滤 | PromptGuard、代码危险词检查、HTML sandbox | 满足 |
| 响应时间合理 | 流式输出和 run.step 进度追踪 | 满足 |
| 多模态生成不白屏等待 | 图像/互动应用生成过程有 trace 和状态 | 满足 |

#### 4. 实现条件符合性

| 赛题描述 | 当前实现 |
| --- | --- |
| 开发环境不限制 | 使用 Web monorepo，Node + Python |
| 智能体框架不限制 | 使用后端 Python agents + Hermes SDK |
| 明确多智能体协同框架 | 文档和代码中明确 agent topology |
| 需稳定运行 | 提供运行说明、健康检查、自动化测试和 smoke |
| 自行构造至少一门课程知识库 | 支持人工智能导论课程、RAG 导入和 seed course；详见 `07_课程知识库与数据说明.md` |
| 使用其他 AI 辅助工具需选用科大讯飞相关工具 | 运行时支持 MiMo，正式提交前在 `05_开源与AI工具使用说明.md` 登记讯飞相关工具名称、版本、用途和证据 |

#### 5. 初赛提交材料对应

| 提交要求 | 当前状态 |
| --- | --- |
| 演示 PPT | 需另行制作，可引用本文档 |
| 可完整运行的多智能体相关文件 | 项目源码、前后端、agent、skill、数据库 schema、脚本齐全 |
| 智能体演示视频 | 需另行录制，可按 `docs/demo_script.md` 和本文档准备 |
| 开发类型不限 | 当前为 Web 应用 |
| 配套文档 | 本目录已补充需求、开发、测试、部署、开源和符合性文档 |
| AI Coding 工具说明 | 已在 `05_开源与AI工具使用说明.md` 中说明 |

详细打包建议见 `08_初赛提交材料清单.md`。

#### 6. 当前验证结论

截至 2026-06-08，软件代码层面具备以下验证入口：

- 前端 lint/build/test：`npm run web:lint && npm run web:build && npm run web:test`。
- 后端 pytest：`cd services/api && ../../.venv/bin/python -m pytest tests -q`。
- 运行时 mock 扫描：`bash scripts/verify_no_mock_runtime.sh .`。
- Agent smoke 和 E2E：纳入 `bash scripts/run_full_validation.sh`。

综合判断：LearnForge V2 的软件代码和配套文档已经覆盖赛题主要功能要求和两个可选加分项，具备参赛初赛演示准备条件。正式提交前建议补充演示 PPT、7 分钟以内演示视频、完整课程知识库目录，并在现场环境提前验证外部模型 API Key 和网络状态。

\newpage

# 07_课程知识库与数据说明

#### LearnForge V2 课程知识库与数据说明

#### 1. 说明目的

赛题要求参赛团队自行构造至少一门完整高校专业课程的初始知识库或文档集作为系统输入。LearnForge V2 默认以“人工智能导论”为核心课程场景，并兼容计算机基础、数据结构与算法、程序设计等计算机相关课程资料导入。

本文件说明课程知识库的范围、数据结构、导入方式、引用追溯和演示用例。

#### 2. 默认课程

| 项目 | 内容 |
| --- | --- |
| 课程 ID | `ai-course` |
| 课程名称 | 人工智能导论 |
| 适用对象 | 计算机、软件工程、人工智能、电子信息等专业本科低年级学生 |
| 课程目标 | 理解人工智能基本概念、搜索、优化、机器学习、神经网络训练、安全验证和工程实践 |
| 系统位置 | `services/api/app/rag/course_seed.py` |

默认课程种子包含以下主题：

| 主题 | 学习意义 | 可生成资源 |
| --- | --- | --- |
| 数学推导基础 | 补齐线性代数、函数、导数、损失函数等先修知识 | 讲解文档、思维导图、练习题 |
| 梯度下降 | 理解机器学习优化的基本机制 | 互动演示、代码练习、题库 |
| 神经网络训练 | 理解前向传播、反向传播、参数更新 | PPT、视频脚本、代码案例 |
| 资源安全验证 | 理解 AI 生成内容的引用、校验和安全边界 | 测试题、安全说明、案例 |
| 动能定理类比 | 通过跨学科类比帮助学生理解优化过程 | 互动 HTML、图解、笔记 |

#### 3. 知识库数据结构

课程资料导入后，后端会形成以下数据对象：

| 数据对象 | 说明 |
| --- | --- |
| `course_documents` | 原始课程文档，例如章节讲义、实验说明、阅读材料 |
| `document_chunks` | 经过解析和切分后的 RAG 文本块 |
| `source_refs` | 资源生成时携带的来源引用，包含 course_id、document_id、chunk_id |
| `knowledge_points` | 课程知识点，例如梯度下降、损失函数、反向传播 |
| `knowledge_edges` | 知识点先修关系，例如导数 -> 梯度 -> 梯度下降 |
| `resources` | 根据知识库生成的讲解、题目、代码、视频脚本等学习资源 |

#### 4. 导入方式

#### 4.1 API 导入

启动后端后，可用以下命令导入课程文档：

```bash
curl -X POST http://127.0.0.1:8001/api/courses/ai-course/documents \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "人工智能导论-梯度下降",
    "content": "# 梯度下降\n梯度下降是一类用于最小化目标函数的迭代优化方法……"
  }'
```

系统会自动完成解析、切分、保存 chunk、生成 source_refs，并让后续资源生成可以引用该资料。

#### 4.2 脚本导入

项目提供课程资料导入脚本：

```bash
python scripts/import_learning_knowledge.py
```

视频推荐资料可通过以下脚本导入或刷新：

```bash
python scripts/import_bilibili_videos.py
```

#### 5. RAG 与引用追溯

LearnForge V2 的课程知识库不是只作为静态素材展示，而是进入资源生成和校验流程：

1. KnowledgeAgent 根据学生问题检索相关 chunk。
2. ResourceBundleAgent 和各类 Skill 使用 chunk 内容生成个性化资源。
3. 资源对象携带 `source_refs`，用于标注来源。
4. VerifierAgent 检查资源是否有引用、题目答案是否一致、代码是否存在危险模式。
5. 前端以资源卡和 Canvas App 展示生成内容。

这种设计用于解决大模型教育内容常见的“说得像真的但无法追溯”问题。

#### 6. 演示用学生画像与课程用例

正式演示可以使用以下画像样例：

```
我是软件工程大一学生，Python 基础一般，数学推导比较弱，想学神经网络，
喜欢图解和代码，每周能学习 4 小时，希望先补齐梯度下降。
```

可演示任务：

| 任务 | 预期系统行为 |
| --- | --- |
| 构建画像 | 抽取专业、年级、目标、基础、薄弱点、偏好、节奏等不少于 6 个维度 |
| 生成资源包 | 输出讲解文档、思维导图、练习题、阅读材料、代码案例、视频脚本等至少 5 类资源 |
| 生成学习路径 | 将数学推导基础放在前置阶段，并推送梯度下降相关资源 |
| 智能辅导 | 用文字、Markdown、图解、视频推荐或互动演示解释知识点 |
| 学习效果评估 | 提交 Quiz 后更新掌握度、误区和 Dashboard 证据链 |

#### 7. 数据合规说明

- 默认课程资料为团队自构造的教学示例和课程知识点，不包含学生真实隐私数据。
- 系统可以接入外部视频推荐，相关视频版权归原作者和平台所有，LearnForge V2 仅做学习推荐和嵌入展示。
- 提交作品时若加入学校真实课程资料，应确认资料授权范围，并避免公开未授权教材全文。
- 学生画像和学习记忆仅用于个性化推荐、路径规划和学习效果评估，正式部署时应配置用户隔离和隐私策略。

\newpage

# 08_初赛提交材料清单

#### LearnForge V2 初赛提交材料清单

#### 1. 提交目标

本清单根据 A3 赛题页面的初赛作品提交要求整理，用于检查 LearnForge V2 是否具备完整提交条件。正式提交时，应以大赛平台最新通知为准。

#### 2. 材料清单

| 序号 | 赛题要求 | LearnForge V2 提交材料 | 当前状态 |
| --- | --- | --- | --- |
| 1 | 演示 PPT | 展示应用价值、前沿 AI 技术融合思路、实现方法、创新价值和核心功能 | 需另行制作，可直接引用本目录文档 |
| 2 | 可完整运行的多智能体相关文件 | 项目源码、前端、后端、Agent、Skill、数据库 schema、脚本、环境变量示例 | 已具备 |
| 3 | 数据集、模型部署配置文件等 | `07_课程知识库与数据说明.md`、课程导入脚本、`.env.example`、数据库 schema | 已具备基础材料，提交前可补充完整课程资料目录 |
| 4 | 智能体演示视频，7 分钟以内 | 按 `docs/demo_script.md` 录制操作流程、核心功能、多模态生成效果和 AI 技术应用成果 | 需另行录制 |
| 5 | 智能体开发类型不限 | Web 应用，React + FastAPI | 已具备 |
| 6 | 配套文档 | `docs/competition_submission/` 全套文档 | 已具备 |
| 7 | 使用 AI Coding 工具需说明 | `05_开源与AI工具使用说明.md` | 已具备，正式提交前补实际工具名称和截图证据 |

#### 3. 建议提交目录结构

```
LearnForgeV2_A3_Submission/
  source/
    apps/
    packages/
    services/
    scripts/
    requirements/
    package.json
    package-lock.json
    docker-compose.yml
    .env.example
  docs/
    competition_submission/
    demo_script.md
    open_source_licenses.md
    provider_declaration.md
    test_report.md
  data/
    ai-course/
      README.md
      course_documents/
      import_notes.md
  validation/
    test_report.md
    requirement_results.json
    source_truth_manifest.json
  presentation/
    LearnForgeV2_A3_演示PPT.pptx
  video/
    LearnForgeV2_A3_演示视频.mp4
```

#### 4. 演示 PPT 建议结构

| 页码 | 内容 |
| --- | --- |
| 1 | 项目标题、赛题、团队信息 |
| 2 | 高等教育个性化学习痛点 |
| 3 | LearnForge V2 总体方案 |
| 4 | 多智能体协同架构 |
| 5 | 对话式画像构建与 EduMem0 记忆 |
| 6 | 多模态资源生成能力 |
| 7 | 个性化学习路径与资源推送 |
| 8 | 智能辅导和学习效果评估 |
| 9 | RAG、防幻觉和内容安全机制 |
| 10 | 前端体验和学习画布 |
| 11 | 测试验证与运行状态 |
| 12 | 创新价值、应用前景和后续计划 |

#### 5. 7 分钟演示视频建议脚本

| 时间 | 内容 |
| --- | --- |
| 0:00-0:30 | 说明赛题背景和 LearnForge V2 定位 |
| 0:30-1:20 | 注册/登录，使用自然语言完成画像构建 |
| 1:20-2:20 | 输入学习需求，展示智能体 trace 和流式输出 |
| 2:20-3:30 | 生成至少 5 类资源，展示文档、思维导图、题目、代码、视频/图像/互动应用 |
| 3:30-4:30 | 展示个性化学习路径、阶段顺序和资源推送 |
| 4:30-5:20 | 演示智能辅导、Markdown、AppLink 和 Canvas App |
| 5:20-6:10 | 完成 Quiz，展示掌握度、误区和 Dashboard 证据链 |
| 6:10-6:45 | 展示防幻觉、source_refs、Verifier 和系统状态 |
| 6:45-7:00 | 总结创新点和应用价值 |

#### 6. 提交前检查

| 检查项 | 命令或材料 |
| --- | --- |
| 前端 lint/build/test | `npm run web:lint && npm run web:build && npm run web:test` |
| 后端 pytest | `cd services/api && ../../.venv/bin/python -m pytest tests -q` |
| 全量验证 | `bash scripts/run_full_validation.sh` |
| 密钥扫描 | `bash scripts/secret_scan.sh .` |
| 外部服务状态 | 访问 `/api/system/status` |
| 开源协议说明 | 检查 `05_开源与AI工具使用说明.md` 和 `docs/open_source_licenses.md` |
| AI Coding 说明 | 补充实际使用的科大讯飞相关工具名称、版本、用途和截图证据 |
| 课程资料 | 确认至少一门课程资料目录或导入记录随包提交 |

#### 7. 注意事项

- 不要提交真实 API Key、个人账号 Cookie、未授权教材全文或学生真实隐私数据。
- 演示前提前检查网络、模型额度、图像生成额度和 B站播放器可访问性。
- 如果外部模型暂时不可用，系统会在状态页显示 blocked；演示时应准备可说明的运行状态和备用流程。
- 视频时长控制在 7 分钟以内，重点展示可运行系统，而不是只讲架构图。
