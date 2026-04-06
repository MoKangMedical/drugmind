# 💊 DrugMind — 药物研发数字分身协作平台

> **开源的药物研发 Second Me**
> 让药物研发团队的判断力变成可协作的AI分身
> 红杉论点：交付"团队协作结果"，而非卖协作工具

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Version](https://img.shields.io/badge/Version-1.0.0-brightgreen)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🎯 一句话

**药物研发人员的AI数字分身平台，让团队判断力7×24在线协作。**

一个药物化学家的 Second Me + 一个生物学家的 Second Me + 一个药理学家的 Second Me = 一个永不下班的虚拟药物研发团队。

---

## 💰 商业定位

> 红杉：下一代万亿美元公司是"伪装成服务公司的软件公司"

DrugMind 不是卖协作工具，是卖**团队决策结果**。

---

## 🏗️ 架构

```
┌──────────────────────────────────────────────────────┐
│                   DrugMind v1.0                      │
├──────────┬──────────┬──────────┬──────────┬──────────┤
│ 🧪 药物化│ 🔬 生物学│ 💉 药理学│ 📊 数据科│ 📋 项目  │
│ 学家     │ 家       │ 家       │ 学家     │ 负责人   │
│ Second Me│ Second Me│ Second Me│ Second Me│ Second Me│
├──────────┴──────────┴──────────┴──────────┴──────────┤
│         💬 协作讨论引擎 (辩论/共识/决策追踪)          │
├──────────────────────────────────────────────────────┤
│         🧬 药物建模引擎 (对接MediPharma工具链)         │
├──────────────────────────────────────────────────────┤
│         📋 项目管理 (看板/化合物追踪/预算)             │
├──────────────────────────────────────────────────────┤
│         🌐 REST API + WebSocket 实时讨论              │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

```bash
# 克隆
git clone https://github.com/MoKangMedical/drugmind.git
cd drugmind

# 安装
pip install -r requirements.txt

# 启动API服务
python main.py serve --port 8096

# CLI: 创建讨论
python main.py discuss --topic "Compound #47 是否进入先导优化？"

# CLI: 创建项目
python main.py project --name "MG新药" --target CHRM1

# CLI: 创建数字分身
python main.py twin --role medicinal_chemist --name "张博士"
```

---

## 📁 项目结构

```
drugmind/
├── main.py                    # 入口：API服务 + CLI
├── requirements.txt
├── digital_twin/              # 数字分身引擎
│   ├── engine.py              # 分身主引擎
│   ├── personality.py         # 人格配置系统
│   ├── memory.py              # 知识记忆系统
│   └── roles/                 # 5个预设药物研发角色
│       ├── medicinal_chemist.py
│       ├── biologist.py
│       ├── pharmacologist.py
│       ├── data_scientist.py
│       └── project_lead.py
├── collaboration/             # 协作讨论引擎
│   ├── discussion.py          # 结构化讨论
│   ├── debate.py              # 角色辩论
│   ├── consensus.py           # 共识形成
│   └── decision_log.py        # 决策追踪
├── drug_modeling/             # 药物建模桥接
│   ├── molecular_viewer.py    # 分子可视化
│   ├── admet_bridge.py        # ADMET预测桥接
│   └── compound_tracker.py    # 化合物追踪
├── project/                   # 项目管理
│   ├── kanban.py              # 项目看板
│   └── budget.py              # 预算管理
├── api/                       # REST + WebSocket API
│   ├── api.py                 # FastAPI路由
│   ├── ws.py                  # WebSocket实时讨论
│   └── models.py              # 数据模型
└── second_me/                 # Second Me集成层
    ├── bridge.py              # Second Me桥接
    └── trainer.py             # 分身训练器
```

---

## 🔗 相关项目

- **MediPharma**: https://github.com/MoKangMedical/medi-pharma （药物发现工具链）
- **MediChat-RD**: https://github.com/MoKangMedical/medichat-rd （罕见病AI诊断）
- **MediSlim**: https://github.com/MoKangMedical/medi-slim （消费医疗）
- **Second Me**: https://github.com/mindverse/Second-Me （数字分身基座）

---

*DrugMind v1.0 | 2026年4月*
*让药物研发团队的判断力7×24在线协作*
