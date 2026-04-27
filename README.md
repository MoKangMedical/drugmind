# 🔬 DrugMind

> **药物研发数字孪生协作平台** — 从靶点发现到真实世界数据，AI驱动的全管线药物研发协作平台

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

---

## 一句话定义

**从靶点发现到真实世界数据（RWD），AI驱动的全管线药物研发协作平台。**

DrugMind 通过数字孪生技术，构建药物研发全生命周期的虚拟镜像，让靶点发现、分子设计、ADMET预测、临床试验模拟、真实世界数据分析在统一平台上高效协作。

---

## 🎯 核心功能

### 1. 🧬 靶点发现
- 基于知识图谱的靶点识别与验证
- 整合基因组学、蛋白质组学、文献挖掘
- 靶点可成药性评分与优先级排序
- 支持 GWAS、孟德尔随机化等因果推断方法

### 2. 💊 分子设计
- AI 驱动的分子生成（VAE、GAN、扩散模型）
- 基于结构的虚拟筛选（分子对接、药效团模型）
- 先导化合物优化（多目标优化、ADMET约束）
- 分子属性预测与类药性评估

### 3. 📊 ADMET 预测
- **吸收**：口服生物利用度、肠渗透性预测
- **分布**：血浆蛋白结合率、组织分布预测
- **代谢**：CYP450 酶代谢、代谢稳定性预测
- **排泄**：肾清除率、胆汁排泄预测
- **毒性**：hERG 毒性、肝毒性、致突变性预测

### 4. 🏥 临床试验模拟
- 虚拟患者群体生成与入组模拟
- 临床终点预测与统计功效分析
- 试验设计方案优化（剂量、对照、分层）
- 自适应试验设计支持

### 5. 📈 真实世界数据（RWD）
- 电子病历（EMR）数据整合与分析
- 医保索赔数据分析
- 真实世界证据（RWE）生成
- 药物警戒与安全性监测

### 6. 🪞 数字孪生
- 药物研发全管线的数字镜像
- 靶点孪生：基因-疾病-药物网络建模
- 分子孪生：化合物-活性-ADMET 虚拟评估
- 试验孪生：虚拟患者-终点-统计功效模拟
- 市场孪生：RWD-RWE-竞争格局分析

### 7. 👥 协作空间
- 多团队实时协作与角色管理
- 项目管线可视化看板
- 数据、模型、结果的安全共享
- 审计追踪与版本控制

### 8. 📋 监管合规
- FDA IND/NDA 申报材料生成
- NMPA 法规要求遵循
- GCP/GLP 合规检查
- 电子签名与审计日志

---

## 🏗️ 技术架构

```
┌──────────────────────────────────────────────────────────────────┐
│                        DrugMind Platform                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Web 前端   │  │  API 网关   │  │  小程序端    │             │
│  │  React/Vue  │  │  FastAPI    │  │  WeChat     │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         └────────────────┼────────────────┘                     │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   微服务层                                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │   │
│  │  │靶点发现   │ │分子设计   │ │ADMET预测  │ │临床模拟   │    │   │
│  │  │Service   │ │Service   │ │Service   │ │Service   │    │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │   │
│  │  │RWD分析    │ │数字孪生   │ │协作空间   │ │监管合规   │    │   │
│  │  │Service   │ │Engine    │ │Service   │ │Service   │    │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   AI 引擎层                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │ LLM (GPT/    │  │ 分子生成模型  │  │ ADMET预测模型 │    │   │
│  │  │  DeepSeek)   │  │ (VAE/GAN)    │  │ (GNN/RF)     │    │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   数据层                                   │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │   │
│  │  │ChEMBL  │ │PubMed  │ │Clinical│ │OpenFDA │ │本地数据  │ │   │
│  │  │2.4M化合物│ │36M文献 │ │Trials  │ │上市数据 │ │EMR/RWD │ │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术选型 |
|------|---------|
| 前端 | React + TypeScript + Ant Design |
| 后端 | Python + FastAPI + Celery |
| AI引擎 | PyTorch + RDKit + DeepChem |
| 数据库 | PostgreSQL + Neo4j + Redis |
| 消息队列 | RabbitMQ |
| 容器化 | Docker + Kubernetes |
| 监控 | Prometheus + Grafana |

---

## 📖 应用场景

### 场景一：新靶点发现与验证
研究人员输入目标疾病（如非小细胞肺癌），DrugMind 自动检索知识图谱，识别潜在靶点，评估可成药性，输出靶点优先级排名。

### 场景二：先导化合物优化
基于已知活性化合物，AI 生成结构类似物，预测 ADMET 属性，多目标优化平衡活性与成药性，输出候选分子清单。

### 场景三：临床试验设计
输入候选药物信息和目标适应症，系统模拟虚拟患者群体，预测临床终点，优化试验设计方案，生成统计分析计划。

### 场景四：上市后监测
整合真实世界数据，监测药物安全性信号，生成真实世界证据，支持监管申报和市场策略。

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/MoKangMedical/drugmind.git
cd drugmind
pip install -r requirements.txt
```

### 运行靶点发现

```bash
python src/target_discovery.py --disease "非小细胞肺癌" --top-k 10
```

### 运行分子设计

```bash
python src/molecular_design.py --target "EGFR" --num-molecules 100
```

### 运行 ADMET 预测

```bash
python src/admet_predictor.py --input molecules.sdf --output admet_results.csv
```

---

## 📚 API 文档

启动服务后访问 API 文档：

```bash
# 启动 API 服务
uvicorn main:app --host 0.0.0.0 --port 8000

# 访问 Swagger 文档
open http://localhost:8000/docs

# 访问 ReDoc 文档
open http://localhost:8000/redoc
```

### 核心 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/targets/discover` | POST | 靶点发现 |
| `/api/v1/targets/{id}` | GET | 靶点详情 |
| `/api/v1/molecules/generate` | POST | 分子生成 |
| `/api/v1/molecules/optimize` | POST | 分子优化 |
| `/api/v1/admet/predict` | POST | ADMET 预测 |
| `/api/v1/clinical/simulate` | POST | 临床试验模拟 |
| `/api/v1/rwd/analyze` | POST | RWD 分析 |
| `/api/v1/twin/create` | POST | 创建数字孪生 |
| `/api/v1/collaboration/spaces` | GET | 协作空间列表 |

---

## 🐳 部署指南

### Docker 部署

```bash
# 构建镜像
docker build -t drugmind:latest .

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### Kubernetes 部署

```bash
# 部署到 K8s
kubectl apply -f k8s/

# 查看状态
kubectl get pods -n drugmind
```

### 环境变量

```bash
# 复制示例配置
cp .env.example .env

# 必需配置
DATABASE_URL=postgresql://user:pass@localhost/drugmind
REDIS_URL=redis://localhost:6379
NEO4J_URI=bolt://localhost:7687
OPENAI_API_KEY=your-api-key
```

---

## 📁 项目结构

```
drugmind/
├── src/                    # 核心源码
│   ├── target_discovery.py # 靶点发现模块
│   ├── molecular_design.py # 分子设计模块
│   ├── admet_predictor.py  # ADMET预测模块
│   └── main.py             # 主入口
├── data/                   # 数据文件
│   ├── targets.json        # 药物靶点数据
│   └── pipeline.json       # 管线模板
├── docs/                   # 文档
│   └── methodology.md      # 方法论文档
├── examples/               # 示例
│   └── case-study.md       # 案例研究
├── api/                    # API 路由
├── digital_twin/           # 数字孪生引擎
├── drug_modeling/          # 药物建模
├── collaboration/          # 协作模块
├── frontend/               # 前端代码
├── tests/                  # 测试
├── docker-compose.yml      # Docker 编排
├── Dockerfile              # Docker 构建
├── requirements.txt        # Python 依赖
└── main.py                 # 应用入口
```

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

---

## 🔗 相关项目

| 项目 | 定位 |
|------|------|
| [OPC Platform](https://github.com/MoKangMedical/opcplatform) | 一人公司全链路学习平台 |
| [Digital Sage](https://github.com/MoKangMedical/digital-sage) | 与100位智者对话 |
| [Cloud Memorial](https://github.com/MoKangMedical/cloud-memorial) | AI思念亲人平台 |
| [天眼 Tianyan](https://github.com/MoKangMedical/tianyan) | 市场预测平台 |
| [MediChat-RD](https://github.com/MoKangMedical/medichat-rd) | 罕病诊断平台 |
| [MedRoundTable](https://github.com/MoKangMedical/medroundtable) | 临床科研圆桌会 |
| [DrugMind](https://github.com/MoKangMedical/drugmind) | 药物研发数字孪生 |
| [MediPharma](https://github.com/MoKangMedical/medi-pharma) | AI药物发现平台 |
| [Minder](https://github.com/MoKangMedical/minder) | AI知识管理平台 |
| [Biostats](https://github.com/MoKangMedical/Biostats) | 生物统计分析平台 |

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

**🔬 DrugMind** — 让药物研发更智能、更高效、更协同。
