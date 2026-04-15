# DrugMind v2.0

> 🧬 **药物研发人员的数字分身协作平台** — Second Me for Pharma

[![GitHub](https://img.shields.io/badge/GitHub-MoKangMedical/drugmind-blue)](https://github.com/MoKangMedical/drugmind)
[![API](https://img.shields.io/badge/API-v2.0-green)](http://43.128.114.201:8096/docs)

## 🎯 这是什么？

**让每一位药物研发人员拥有自己的AI数字分身，7×24与其他研发人员的分身讨论药物项目。**

想象一下：
- 药物化学家张博士下班了，但他的数字分身还在回答其他团队的问题
- 投资人想了解一个靶点，直接问5个不同专业角度的数字分身
- AI制药创业团队人手不够，但可以有"10个虚拟专家"7×24协作

**类比**：GitHub让代码协作变成异步的，DrugMind让药物研发讨论变成异步的。

## 🚀 快速开始

```bash
# 克隆
git clone https://github.com/MoKangMedical/drugmind.git
cd drugmind

# 部署
bash deploy.sh 8096

# 或者Docker
docker-compose up -d
```

访问 http://localhost:8096

## 📡 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v2/twins` | GET/POST | 数字分身管理 |
| `/api/v2/twins/{id}/ask` | POST | 向分身提问 |
| `/api/v2/discussions` | POST | 创建讨论 |
| `/api/v2/discussions/{id}/run` | POST | 运行讨论 |
| `/api/v2/hub` | GET/POST | 公开讨论广场 |
| `/api/v2/second-me/create` | POST | 创建Second Me分身 |
| `/api/v2/second-me/{id}/chat` | POST | Second Me对话 |
| `/api/v2/projects` | POST | 项目管理 |
| `/api/v2/compounds` | POST | 化合物追踪 |
| `/api/v2/admet` | POST | ADMET预测 |

完整文档：http://localhost:8096/docs

## 🏗️ 架构

```
drugmind/
├── digital_twin/      # 数字分身引擎
│   ├── engine.py      # 分身管理+MIMO推理
│   ├── personality.py # 人格系统
│   ├── memory.py      # HMM三层记忆
│   └── roles/         # 预设角色定义
├── collaboration/     # 协作讨论引擎
│   ├── discussion.py  # 结构化讨论
│   ├── consensus.py   # 共识形成
│   └── decision_log.py# 决策追踪
├── drug_modeling/     # 药物建模桥接
│   ├── admet_bridge.py
│   └── compound_tracker.py
├── auth/              # 用户系统
├── community/         # 公开讨论广场
├── second_me/         # Second Me集成
│   ├── integration.py # 云端+本地双模式
│   ├── bridge.py
│   └── trainer.py
├── api/               # REST API + WebSocket
├── frontend/          # Web界面
└── main.py            # CLI入口
```

## 🧪 5个预设角色

| 角色 | 关注点 | 风险容忍 |
|------|--------|---------|
| 🧪 药物化学家 | 合成可行性/SAR/路线设计 | 0.3 (保守) |
| 🔬 生物学家 | 靶点验证/活性/选择性 | 0.5 (平衡) |
| 💊 药理学家 | 安全性/ADMET/hERG | 0.2 (最保守) |
| 📊 数据科学家 | ML建模/数据分析/QSAR | 0.7 (偏激进) |
| 📋 项目负责人 | Go/No-Go/资源/商业 | 0.4 (稳健) |

支持自定义角色和用户创建专属数字分身。

## 🔗 Second Me集成

DrugMind与 [Second Me](https://github.com/mindverse/Second-Me) 深度集成：

- **云端模式**：连接 app.secondme.io，无需本地部署
- **本地模式**：连接本地Second Me实例（需8GB+内存）
- **训练数据**：药物研发垂直领域的知识注入
- **HMM记忆**：三层记忆建模，让分身越用越懂你

## 💰 商业模式

| 层级 | 价格 | 功能 |
|------|------|------|
| 免费 | $0 | 2个分身，基础讨论 |
| 专业 | $29/月 | 无限分身，项目空间 |
| 团队 | $99/月 | 5人团队，私有部署 |
| 企业 | 联系销售 | 私有化部署 |

> **红杉铁律**：不是卖工具，是卖"7×24在线的研发团队判断力"。

## 📄 许可证

Apache 2.0

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=MoKangMedical/drugmind&type=Date)](https://star-history.com/#MoKangMedical/drugmind&Date)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License
