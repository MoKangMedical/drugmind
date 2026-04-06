# DrugMind × Second Me 对接指南

## 架构

```
你的 Mac Mini (16GB)                腾讯云服务器 (3.6GB)
┌─────────────────────┐            ┌──────────────────────┐
│  Second Me 本地实例   │ ◄───────► │  DrugMind v2.0       │
│  localhost:8002      │  HTTP API │  43.128.114.201:8096  │
│  llama.cpp + Qwen2.5 │           │  MIMO API + 前端      │
│  HMM记忆建模          │           │  数字分身+讨论引擎     │
└─────────────────────┘            └──────────────────────┘
```

## 开发者控制台 Integration 配置

在 Second Me 开发者控制台创建 Integration 时，直接使用下面这组配置：

### Skill Metadata

| 字段 | 值 |
|------|----|
| Integration Key | `drugmind` |
| Display Name | `DrugMind — 药物研发AI协作平台` |
| Description | `AI驱动的药物研发数字分身协作平台，提供多角度专业分析、团队讨论、ADMET评估和化合物管理功能。让所有想制药的人，有一个专业的地方讨论、协作、推进项目。` |
| Keywords | `drug discovery, pharma, medicinal chemistry, ADMET, AI制药, 药物研发` |

### Prompts

| 字段 | 值 |
|------|----|
| Activation Short | `药物研发讨论` |
| Activation Long | `当你需要药物研发相关的专业分析时，使用DrugMind。它会从药物化学、生物学、药理学、数据科学、项目管理五个角度给出专业回答。` |
| System Summary | `DrugMind是一个药物研发数字分身协作平台。支持多角色AI问答、5人团队讨论、ADMET评估、化合物管线管理和场景模板。` |

### Actions

| Action Name | Description | Tool Name |
|-------------|-------------|-----------|
| `AI专业问答` | 向药物研发AI团队提问，获得多角度专业分析 | `drugmind_ask` |
| `团队讨论` | 5个专业数字分身围绕药物研发议题进行讨论 | `drugmind_discuss` |
| `ADMET评估` | 快速评估化合物的ADMET性质 | `drugmind_admet` |
| `场景模板` | 获取药物研发场景检查清单 | `drugmind_scenario` |
| `化合物管理` | 管理化合物管线 | `drugmind_compound` |

### MCP Configuration

| 字段 | 值 |
|------|----|
| MCP Endpoint | `http://43.128.114.201:8096/api/mcp` |
| Timeout (ms) | `60000` |
| Auth Mode | `none` |
| Allowed Tools | `drugmind_ask, drugmind_discuss, drugmind_admet, drugmind_scenario, drugmind_compound` |

### OAuth Binding

| 字段 | 值 |
|------|----|
| OAuth App ID | 在 Second Me 控制台创建 OAuth App 后填写 |
| Required Scopes | `userinfo` |

### Environment Bindings

| 环境 | Enabled | Endpoint Override |
|------|---------|-------------------|
| `pre` | ✅ | `http://43.128.114.201:8096/api/mcp` |
| `prod` | ✅ | `http://43.128.114.201:8096/api/mcp` |

### 推荐填写顺序

1. 先创建 OAuth App，拿到 App ID。
2. 再创建 Integration，填入上面的 Skill Metadata、Prompts、Actions 和 MCP 配置。
3. MCP Endpoint 先使用 `http://43.128.114.201:8096/api/mcp`。
4. Auth Mode 先选 `none`，后续如果要接入用户级别授权，再切换为 `bearer_token`。

## 第一步：在Mac Mini上部署Second Me

```bash
# 克隆
git clone https://github.com/mindverse/Second-Me.git
cd Second-Me

# 启动 (Mac M系列会自动用MLX加速)
make docker-up

# 访问 http://localhost:3000 完成初始训练
```

Mac 16GB推荐配置：
- 模型：Qwen2.5-1.5B（平衡性能和内存）
- 如果卡顿：用Qwen2.5-0.8B

## 第二步：让DrugMind连接本地Second Me

在DrugMind的 `.env` 或环境变量中设置：

```bash
# 使用本地模式（替换云端模式）
export SECOND_ME_MODE=local
export SECOND_ME_URL=http://你的Mac内网IP:8002
```

或者通过API切换：

```bash
# 创建Second Me实例时指定本地模式
curl -X POST http://43.128.114.201:8096/api/v2/second-me/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "你的名字",
    "role": "medicinal_chemist",
    "expertise": ["GLP-1", "多肽"],
    "mode": "local",
    "local_url": "http://192.168.1.100:8002"
  }'
```

## 第三步：训练你的数字分身

1. 在Second Me Web界面 (localhost:3000) 上传你的知识：
   - 发表的论文
   - 实验记录
   - 项目文档
   - 会议笔记

2. Second Me会用HMM建模你的知识层次：
   - L0: 原始数据
   - L1: 结构化知识
   - L2: 高层洞察和判断模式

3. 训练完成后，DrugMind会自动识别你的分身并加入讨论

## 第四步：在DrugMind上讨论

访问 http://43.128.114.201:8096，你的分身可以：
- 参与公开讨论
- 加入项目团队讨论
- 被其他用户"提问"
- 自动学习讨论中的新知识

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| DrugMind连不上Second Me | 检查Mac防火墙，确保8002端口开放 |
| Second Me OOM | 用更小的模型（Qwen2.5-0.8B） |
| 回复慢 | 首次加载模型需30秒，之后会缓存 |
| 知识不准确 | 多训练几轮，增加更多原始数据 |
