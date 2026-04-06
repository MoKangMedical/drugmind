# DrugMind × Second Me 本地对接指南

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
