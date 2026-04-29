# 💊 DrugMind — 药物研发数字分身协作平台

> **开源的药物研发Second Me**
> 让药物研发团队的判断力变成可协作的AI分身
> 基于红杉论点：交付"团队协作结果"，而非卖协作工具

---

## 🎯 一句话

**药物研发人员的AI数字分身平台，让团队判断力7×24在线协作。**

一个药物化学家的Second Me + 一个生物学家的Second Me + 一个药理学家的Second Me = 一个永不下班的虚拟药物研发团队。

---

## 💡 核心概念

```
┌─────────────────────────────────────────────────────────────────┐
│                    DrugMind 平台                                │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ 🧪 药物化 │  │ 🔬 生物学 │  │ 💉 药理学 │  │ 📊 数据科 │       │
│  │ 学家Second│  │ 家Second │  │ 家Second │  │ 学家     │       │
│  │ Me       │  │ Me       │  │ Me       │  │ Second Me│       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │             │             │              │
│       └─────────────┴──────┬──────┴─────────────┘              │
│                            │                                    │
│                    ┌───────▼───────┐                           │
│                    │  💬 协作讨论   │                           │
│                    │  📋 项目看板   │                           │
│                    │  🧬 分子建模   │                           │
│                    │  📈 决策记录   │                           │
│                    └───────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ 技术架构

### 四层架构

```
┌─────────────────────────────────────────────────────┐
│ Layer 4: 协作界面                                     │
│ Web UI · 项目看板 · 讨论流 · 分子可视化                │
├─────────────────────────────────────────────────────┤
│ Layer 3: Agent编排层                                  │
│ 角色定义 · 对话管理 · 任务分配 · 共识决策              │
├─────────────────────────────────────────────────────┤
│ Layer 2: 数字分身层 (Second Me)                       │
│ 知识建模 · 人格注入 · 判断力模拟 · 持续学习            │
├─────────────────────────────────────────────────────┤
│ Layer 1: 药物研发工具层                               │
│ 分子建模 · ADMET · 对接 · 文献 · 知识图谱             │
└─────────────────────────────────────────────────────┘
```

### 核心模块

#### 1. 数字分身引擎 (Digital Twin Engine)
基于Second Me架构改造，为药物研发定制：

- **知识注入**：上传专家的论文、实验记录、决策日志
- **思维建模**：学习专家的判断模式（偏好、风险容忍度、创新风格）
- **人格定义**：每个角色有独立的"人格配置"
  ```yaml
  roles:
    medicinal_chemist:
      name: "药物化学家"
      expertise: [SMILES, 命名反应, 合成路线, 分子优化]
      personality: "务实，偏好可合成的分子，风险厌恶"
      tools: [RDKit, 合成可行性评分, retrosynthesis]
      
    biologist:
      name: "生物学家"
      expertise: [靶点验证, 细胞实验, 动物模型, 生物标志物]
      personality: "严谨，注重实验数据，谨慎乐观"
      tools: [文献检索, 实验设计, 数据分析]
      
    pharmacologist:
      name: "药理学家"
      expertise: [PK/PD, 剂量-反应, 毒理学, 安全性评估]
      personality: "保守，安全第一，注重临床转化"
      tools: [ADMET预测, PK模拟, 毒性评估]
      
    data_scientist:
      name: "数据科学家"
      expertise: [ML建模, 统计分析, 分子表示学习, 虚拟筛选]
      personality: "数据驱动，喜欢创新方法，乐观"
      tools: [DeepChem, PyTorch, 分子GNN]
      
    project_lead:
      name: "项目负责人"
      expertise: [项目管理, 资源分配, Go/No-Go决策, 商业评估]
      personality: "全局视角，平衡风险与收益"
      tools: [项目看板, 决策矩阵, 财务模型]
  ```

#### 2. 协作讨论引擎 (Collaboration Engine)
Agent间讨论的机制设计：

- **结构化讨论**：围绕具体议题展开（如"这个化合物值不值得推进"）
- **角色辩论**：不同专业视角碰撞（化学家说能合成，药理学家说毒性太高）
- **共识形成**：投票/权衡/折中方案
- **决策追踪**：记录每个决策的理由和反对意见

```
讨论流程示例：

📋 议题：Compound #47 是否进入先导优化？

🧪 药物化学家 Second Me:
   "合成可行性SA=3.2，中等难度。有3条路线可选，最短5步。
    但C-3位的立体化学控制是个挑战。"

🔬 生物学家 Second Me:
   "活性pIC50=7.2，比先导化合物提升10倍。
    但选择性数据不足，需要测试off-target panel。"

💉 药理学家 Second Me:
   "ADMET预测：Caco2渗透良好，但hERG IC50=8μM，
    有心脏毒性风险。建议加测hERG patch clamp。"

📊 数据科学家 Second Me:
   "分子指纹分析显示与已知心脏毒性药物有23%相似度。
    但PK预测半衰期4.2h，适合BID给药方案。"

📋 项目负责人 Second Me:
   "综合评估：活性✓ 合成性⚠️ 安全性❌ PK✓
    建议：先解决hERG问题再推进。进入先导优化Phase 1，
    重点优化心脏安全性。Budget: $50K, Timeline: 4周。"

✅ 决策：Compound #47 进入先导优化Phase 1
📝 记录：附带hERG风险缓解方案
```

#### 3. 药物建模引擎 (Drug Modeling Engine)
复用MediPharma的工具链：

- 分子可视化（3D结构、对接pose）
- ADMET实时预测
- 合成路线规划
- 活性-毒性权衡图
- 竞品管线追踪

#### 4. 项目管理 (Project Management)
- 药物研发项目看板
- 化合物追踪表（结构-活性-ADMET-合成性）
- 决策日志（Go/No-Go记录）
- 时间线和里程碑
- 预算追踪

---

## 🔧 技术栈

| 层 | 技术 | 开源参考 |
|------|------|----------|
| 前端 | Next.js + React + 3Dmol.js | Second Me UI |
| Agent框架 | CrewAI + LangGraph | CrewAI, ChatDev |
| 数字分身 | HMM记忆建模 + LoRA微调 | Second Me |
| LLM | MIMO API + 本地模型 | Ollama |
| 分子工具 | RDKit + DeepChem + NGLView | MediPharma |
| 后端 | FastAPI + WebSocket | - |
| 数据库 | PostgreSQL + Qdrant(向量) | - |
| 部署 | Docker + K8s | - |

---

## 🎯 使用场景

### 场景1：虚拟团队讨论
一个中国团队的药物化学家和美国的生物学家，他们的Second Me可以7×24讨论，不用等时区。

### 场景2：快速假设验证
"如果我们换一个骨架，ADMET会怎样？" → 5个Second Me同时分析，5分钟出结论。

### 场景3：知识传承
资深专家退休前，把他的判断力固化成Second Me，新团队可以持续学习。

### 场景4：决策审计
每个决策都有完整讨论记录和理由，FDA审计时有据可查。

### 场景5：一人药企放大器
小林医生一个人 + 5个Second Me = 一个完整的虚拟药物研发团队。

---

## 📁 项目结构

```
drugmind/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── digital_twin/              # 数字分身引擎
│   ├── __init__.py
│   ├── twin_builder.py        # 分身构建（知识注入+训练）
│   ├── personality.py         # 人格配置系统
│   ├── memory_model.py        # 层级记忆建模（HMM）
│   ├── reasoning.py           # 推理引擎
│   └── roles/                 # 预设角色
│       ├── medicinal_chemist.py
│       ├── biologist.py
│       ├── pharmacologist.py
│       ├── data_scientist.py
│       └── project_lead.py
├── collaboration/             # 协作引擎
│   ├── __init__.py
│   ├── discussion.py          # 结构化讨论
│   ├── debate.py              # 角色辩论
│   ├── consensus.py           # 共识形成
│   └── decision_log.py        # 决策追踪
├── drug_modeling/             # 药物建模（复用MediPharma）
│   ├── __init__.py
│   ├── molecular_viewer.py    # 分子可视化
│   ├── admet_bridge.py        # ADMET预测桥接
│   ├── synthesis_planner.py   # 合成路线
│   └── competitor_tracker.py  # 竞品追踪
├── project/                   # 项目管理
│   ├── __init__.py
│   ├── compound_tracker.py    # 化合物追踪
│   ├── kanban.py              # 项目看板
│   ├── budget.py              # 预算管理
│   └── timeline.py            # 时间线
├── api/                       # REST + WebSocket API
│   ├── __init__.py
│   ├── api.py                 # FastAPI路由
│   ├── ws.py                  # WebSocket实时讨论
│   └── models.py              # 数据模型
└── frontend/                  # Web界面
    ├── package.json
    ├── src/
    │   ├── pages/
    │   │   ├── dashboard.tsx   # 项目仪表盘
    │   │   ├── discussion.tsx  # 讨论界面
    │   │   ├── molecules.tsx   # 分子查看器
    │   │   └── settings.tsx    # 分身配置
    │   └── components/
    │       ├── AgentChat.tsx   # Agent对话组件
    │       ├── Molecule3D.tsx  # 3D分子可视化
    │       └── DecisionLog.tsx # 决策日志
    └── public/
```

---

## 💰 商业模式（红杉论点）

> 不是卖协作工具，是卖"团队决策结果"

| 收入来源 | 描述 | 目标客户 |
|----------|------|----------|
| 平台订阅 | SaaS版DrugMind | Biotech/学术团队 |
| 分身定制 | 为药企定制行业专家分身 | 大型药企 |
| 数据服务 | 药物研发知识库 | CRO/CDMO |
| 项目加速 | 用DrugMind加速药物发现 | 创新药企 |

---

## 🔗 与MediPharma的关系

```
DrugMind (协作平台)          MediPharma (工具链)
     │                              │
     │   团队讨论决定做哪个靶点       │
     ├──────────────────────────────►│
     │                              │ 靶点发现
     │   讨论筛选策略                │ 虚拟筛选
     ├──────────────────────────────►│ 分子生成
     │                              │ ADMET预测
     │◄──────────────────────────────┤
     │   拿到候选化合物              │
     │   团队讨论优化方向            │
     ├──────────────────────────────►│
     │                              │ 先导优化
     │◄──────────────────────────────┤
     │   最终候选+团队决策记录       │
     └──────────────────────────────┘
```

DrugMind = 大脑（决策+协作）
MediPharma = 双手（执行+计算）

---

## 🚀 开发路线图

### Phase 1: MVP (2周)
- [ ] 基于Second Me搭建数字分身引擎
- [ ] 5个预设药物研发角色
- [ ] 基础讨论界面（文字对话）
- [ ] Docker一键部署

### Phase 2: 协作增强 (4周)
- [ ] 结构化讨论流程
- [ ] 角色辩论模式
- [ ] 决策日志和追踪
- [ ] MediPharma工具集成

### Phase 3: 可视化 (6周)
- [ ] 3D分子查看器
- [ ] 项目看板
- [ ] 实时WebSocket讨论
- [ ] 合成路线可视化

### Phase 4: 商业化 (8周)
- [ ] 多租户SaaS
- [ ] 分身市场（下载/分享分身）
- [ ] 企业版权限管理
- [ ] GitHub Pages推广站

---

*DrugMind | 2026年4月*
*让药物研发团队的判断力7×24在线协作*
