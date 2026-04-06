# DrugMind 多 Agent 平台建设方案

## 目标

DrugMind 不应只做成一个“带几个 AI 功能的药研网站”，而应建设成一个面向药物研发的多 Agent 协作平台：

- 既能让专业 Agent 协作完成研发任务
- 也能让用户、团队、项目、化合物、讨论、结论沉淀为持续可复用资产
- 最终形成可开发、可交付、可商业化、可持续迭代的平台能力

## 顶尖平台对标，不对标表面功能

对标对象不应该只是某一个产品界面，而应该对标顶尖平台的核心能力：

1. 多 Agent 编排能力
2. 稳定的工具调用能力
3. 可持续的项目记忆与知识沉淀
4. 面向团队的协作与任务流
5. 可观测、可评估、可复盘
6. 可权限化、可计费、可产品化

DrugMind 未来的差异化不在“聊天”，而在“围绕药物研发全过程的专业协作闭环”。

## 平台核心公式

在 DrugMind 里，一个真正可工作的 Agent 应该由 7 个部分组成：

`Agent = Role + Skills + Tools + Memory + Workflow + Evaluation + Permissions`

含义如下：

- `Role`：这个 Agent 是谁，站在什么专业视角工作
- `Skills`：它有哪些方法论、判断框架、模板和 SOP
- `Tools`：它能调用哪些平台工具和外部系统
- `Memory`：它记得哪些用户、项目、化合物、实验和历史结论
- `Workflow`：它在什么阶段触发，如何与其他 Agent 交接
- `Evaluation`：如何判断它输出是否可信、是否达标
- `Permissions`：它可以读写哪些项目、数据、结论和资源

## 当前仓库基础

现有仓库已经有 4 个可继续放大的基础层：

- 数字分身层：`digital_twin/`
- 讨论协作层：`collaboration/`
- 药研工具层：`drug_modeling/`
- MCP 对接层：`api/mcp_server.py`

已经具备“原型平台”雏形的文件：

- [digital_twin/engine.py](/Users/apple/Desktop/DrugMind/digital_twin/engine.py)
- [collaboration/discussion.py](/Users/apple/Desktop/DrugMind/collaboration/discussion.py)
- [drug_modeling/compound_tracker.py](/Users/apple/Desktop/DrugMind/drug_modeling/compound_tracker.py)
- [api/mcp_server.py](/Users/apple/Desktop/DrugMind/api/mcp_server.py)
- [api/api.py](/Users/apple/Desktop/DrugMind/api/api.py)
- [auth/user.py](/Users/apple/Desktop/DrugMind/auth/user.py)

但这些能力目前仍偏向单机原型，离顶尖平台还差以下几层：

- 没有统一 agent orchestration 层
- 没有真正的 skills 注册与版本化机制
- 没有工具权限与任务上下文管理
- 没有 durable memory / project memory / evidence graph
- 没有 workflow engine / event bus / async job
- 没有团队、租户、计费、审计、观测体系

## 建议的多 Agent 结构

### A. 平台编排 Agent

这是平台的大脑，不直接做专业判断，而负责：

- 任务拆解
- 角色路由
- 工具分配
- 上下文压缩
- 结果汇总
- 质量校验

建议命名：

- `Orchestrator Agent`
- `Project PM Agent`
- `Review / QA Agent`

### B. 药研专业 Agent

这是 DrugMind 的核心差异化层，建议保留并强化当前 5 个角色：

1. `Medicinal Chemistry Agent`
2. `Biology Agent`
3. `Pharmacology / ADMET Agent`
4. `Data Science / Modeling Agent`
5. `Project / Portfolio Agent`

每个专业 Agent 后续都应拥有：

- 专属 prompt / persona
- 专属 skills
- 专属工具白名单
- 专属评价标准
- 专属输出模板

### C. 平台建设 Agent

为了持续开发产品本身，平台内部还应有建设型 Agent：

1. `Backend Platform Agent`
2. `Frontend Experience Agent`
3. `MCP / Integration Agent`
4. `Data / Knowledge Agent`
5. `Infra / Deployment Agent`

这些 Agent 不是给终端用户直接看到的，而是用来持续建设 DrugMind 自己的平台能力。

### D. 商业化 Agent

如果目标是“开发盈利”，就不能缺少商业化工作流：

1. `Growth Agent`
2. `Customer Success Agent`
3. `Proposal / Report Agent`
4. `Billing / Usage Agent`

这部分能力决定 DrugMind 是否只是一个演示平台，还是一个真实产品。

## Skills 体系怎么建设

平台不应该只保存“角色”，还要保存“技能包”。

建议将 skills 拆成 3 层：

### 1. 通用平台 Skills

- 任务拆解
- 证据汇总
- 报告生成
- 决策记录
- 风险复盘

### 2. 药研专业 Skills

- 靶点评估
- Hit 发现
- Lead 优化
- ADMET 筛查
- PK/PD 解释
- QSAR 建模
- Go/No-Go 决策

### 3. 组织工作 Skills

- 项目周报
- 团队讨论纪要
- 里程碑评审
- 竞品情报整理
- 对外汇报材料生成

## Tools 体系怎么建设

每个 Agent 需要工具，但工具不能散落在 API 里。

建议把工具体系标准化为以下类别：

1. `Knowledge Tools`
   - 文献搜索
   - 专利检索
   - 内部文档检索
   - 实验结果检索

2. `Molecule Tools`
   - ADMET
   - 描述符
   - 相似性搜索
   - SAR 跟踪
   - 化合物库管理

3. `Project Tools`
   - 任务管理
   - 决策日志
   - 项目时间线
   - 负责人分配

4. `Collaboration Tools`
   - 团队讨论
   - 评论
   - 共识提炼
   - 争议点跟踪

5. `Business Tools`
   - 使用量统计
   - 订阅与权限
   - 报价单 / 方案书
   - 客户项目隔离

## 建议的代码结构演进

建议后续新增以下目录，而不是继续把能力塞进当前模块：

```text
agents/               # agent定义、角色、注册表、路由策略
skills/               # skills包、模板、版本
tools/                # 工具注册、权限、schema、执行器
workflows/            # 多步骤任务流、异步作业、事件驱动
memory/               # 项目记忆、用户记忆、证据图谱
evals/                # agent输出评测、质量回归
billing/              # 订阅、配额、商业化
observability/        # 日志、追踪、调用统计、失败分析
```

## 分阶段建设顺序

### Phase 1：平台内核

先把系统从原型升级成平台底座：

- 持久化层改为 SQLite / PostgreSQL
- 用户 / 项目 / 讨论 / 化合物统一数据模型
- 基础权限模型
- 任务与操作日志
- API schema 标准化

### Phase 2：Agent + Skills + Tools

把“角色”升级成真正可工作的 agent：

- agent 注册表
- skills 注册表
- tool registry
- 统一执行上下文
- 统一输出格式

### Phase 3：多 Agent 协作

从单次问答升级到工作流：

- 任务拆解
- agent 分工执行
- 中间结果交接
- 证据归档
- 总结与决策落库

### Phase 4：产品化和商业化

从研发原型升级到可卖产品：

- 多租户
- 配额和权限
- 使用统计
- 订阅方案
- 团队工作台
- 企业交付能力

## 对当前项目最重要的结论

当前 DrugMind 最应该做的，不是继续追加零散功能，而是先完成这 4 件事：

1. 做统一平台数据层
2. 做 agent / skill / tool 注册与编排层
3. 做项目级 memory 和 decision log
4. 做面向团队的 workflow，而不只是单轮问答

## 推荐的近期执行方式

接下来开发应按多 agent 并行推进：

1. 一个 Agent 专门做平台内核和数据层
2. 一个 Agent 专门做 agent/skill/tool 架构
3. 一个 Agent 专门做药研工具链深化
4. 一个 Agent 专门做前端工作台和用户流
5. 一个 Agent 专门做 MCP / Second Me / 外部集成
6. 一个 Agent 专门做评测、监控、质量回归

这样做的结果是：

- 平台本身持续进化
- 专业能力持续增强
- 新工具可以快速接入
- 新 Agent 可以低成本扩展
- 产品可以逐步走向商业化

## 下一步建议

如果按这个方向继续，我建议下一个开发里程碑直接落成：

`Agent Registry + Skill Registry + Tool Registry + Project Memory + Workflow Orchestrator`

这是 DrugMind 从“原型”进入“平台化开发”的分水岭。
