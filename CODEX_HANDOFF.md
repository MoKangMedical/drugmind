# CODEX_HANDOFF.md — Codex接管指南

> 给Codex的项目交接文档。请从这里开始。

## 📦 仓库信息
- GitHub: https://github.com/MoKangMedical/drugmind.git
- 分支: main
- 启动: `python3 main.py serve --port 8096`

## 🏗️ 项目架构

```
drugmind/
├── main.py              # 入口 CLI
├── llm.py               # MIMO API调用封装
├── api/                 # FastAPI后端
│   ├── api.py           # REST端点 (25+个)
│   ├── mcp_server.py    # MCP协议端点 (Second Me)
│   └── models.py        # 数据模型
├── digital_twin/        # AI数字分身系统
│   ├── engine.py        # 分身引擎 (创建/对话/记忆)
│   ├── personality.py   # 人格系统
│   ├── memory.py        # 分层记忆
│   └── roles/           # 5个专业角色定义
├── community/           # 讨论广场 (Feed流)
├── collaboration/       # 协作系统 (讨论/共识/决策日志)
├── drug_modeling/       # 药物建模工具
│   ├── admet_bridge.py  # ADMET评估 (RDKit)
│   └── compound_tracker.py # 化合物管线
├── seeds/               # 种子数据 (8个AI制药话题)
├── second_me/           # Second Me集成
├── project/             # 项目管理看板
├── auth/                # 用户系统
├── frontend/            # Web前端 (SPA)
│   ├── index.html       # 单页应用入口
│   ├── css/style.css    # 暗色主题
│   └── js/app.js        # 完整交互
├── miniapp/             # 微信小程序框架
├── docs/                # 文档
│   ├── PRODUCT_DESIGN.md
│   ├── SECOND_ME_SETUP.md
│   └── secondme-integration.json
├── Dockerfile           # Docker部署
└── deploy.sh            # 部署脚本
```

## 🔑 核心依赖

```bash
pip install fastapi uvicorn httpx rdkit
```

## 🚀 快速启动

```bash
git clone https://github.com/MoKangMedical/drugmind.git
cd drugmind
pip install -r requirements.txt

# 设置环境变量
export MIMO_BASE_URL="https://api.xiaomimimo.com/v1"
export MIMO_API_KEY="your-mimo-api-key"

# 启动
python3 main.py serve --port 8096
```

## 🧬 核心功能

### 1. 5个AI数字分身
- 药物化学家(陈化学家🧪) - SMILES/合成/分子优化
- 生物学家(王生物🔬) - 靶点验证/功能基因组学
- 药理学家(李药理💊) - ADMET/毒理学/临床药理
- 数据科学家(赵数据📊) - AI/ML/QSAR建模
- 项目负责人(刘总监📋) - 项目管理/商业评估

### 2. MCP协议端点 (Second Me接入)
- 端点: `POST /api/mcp`
- 支持: `tools/list` + `tools/call`
- 5个工具: ask/discuss/admet/scenario/compound

### 3. REST API
- 用户: register/login/profile
- 分身: create/ask/teach/memory
- 讨论: create/run/summary
- Hub: post/list/search/like/reply
- 工具: admet/pipeline/scenarios

## 📊 当前状态
- 服务器: 运行在 43.128.114.201:8096
- 数据: 10个分身, 3个种子讨论, 5个专业角色
- 前端: 完整SPA, 暗色主题, 响应式
- MCP: 5个工具可用, Second Me可直接调用

## 🎯 待优化方向
1. **真实用户系统**: 集成微信登录
2. **数据持久化**: SQLite/PostgreSQL替换JSON文件
3. **分身训练**: 接入用户真实知识数据
4. **化合物可视化**: 分子结构3D展示
5. **讨论记录持久化**: 目前讨论仅内存存储
6. **WebSocket实时**: 当前讨论是同步的,可改为WebSocket

## ⚠️ 注意事项
- MIMO API密钥是核心资源, 妥善保管
- 服务器3.6GB内存限制, 不要加载过大的模型
- RDKit已安装, 可直接使用
- 前端是纯HTML/CSS/JS, 无外部依赖
- 微信小程序代码在miniapp/目录, 需要用开发者工具打开

## 📞 联系
- GitHub: MoKangMedical
- Second Me: xiaolin110
