# GitHub Pages 调试指南

## 目标

GitHub Pages 只负责托管 DrugMind 的静态前端。

后端 API、MCP、FastAPI 文档仍然运行在你自己的服务器上。  
因此 GitHub Pages 的正确使用方式是：

- Pages 负责前端页面
- 页面通过 `API Base URL` 连接真实后端
- 所有动态功能都通过这个后端调试

## 已接入的 Pages 机制

仓库已经加入：

- Pages 工作流：`/.github/workflows/deploy-pages.yml`
- 前端运行时配置：`/frontend/js/config.js`
- 页面调试面板：打开站点后即可配置 API 端点
- `.nojekyll`：避免 GitHub Pages 对静态文件做 Jekyll 处理

## 必须知道的限制

1. GitHub Pages 不能运行 FastAPI
2. GitHub Pages 页面不能安全调用 HTTP 后端
3. 所以用于联调的后端地址必须是 HTTPS

如果你把页面部署到 GitHub Pages，但后端还是：

`http://43.128.114.201:8096`

那么浏览器会因为 Mixed Content 拒绝请求。

## 推荐接法

### 方式 A：给后端配正式 HTTPS 域名

例如：

`https://api.drugmind.ai`

这是最稳妥的方案。

### 方式 B：先用 Cloudflare Tunnel

例如当前联调用过的：

`https://testing-pixels-homepage-son.trycloudflare.com`

这个可以用于调试，但不是长期稳定地址。

## GitHub Pages 工作流如何取 API 地址

工作流会读取仓库变量：

`PAGES_API_BASE_URL`

你在 GitHub 仓库里设置它之后，Pages 发布时会把它写进前端运行时配置。

推荐填：

`https://你的后端域名`

不要包含路径，不要写成 `/api/v2`。

## 页面里怎么调试

部署后打开 GitHub Pages 页面：

1. 顶部点击“调试配置”
2. 填入 `API Base URL`
3. 点击“保存端点”
4. 点击“检测 /health”
5. 再依次测试：
   - 最新讨论
   - AI 团队加载
   - 快速提问
   - ADMET 评估
   - API Docs
   - MCP Endpoint

## 当前适合在 Pages 上调试的功能

- `/health`
- `/api/v2/stats`
- `/api/v2/roles`
- `/api/v2/hub`
- `/api/v2/quick-ask`
- `/api/v2/admet`
- `/api/v2/platform/*`
- `/api/v2/projects/*`
- `/api/v2/workflows/*`

## 不适合直接依赖 Pages 调试的部分

- 本地文件系统持久化行为
- 服务器侧日志
- 需要长连接保证的临时隧道
- HTTP-only 的旧后端地址

## 发布后的建议顺序

1. 先让后端有稳定 HTTPS 地址
2. 再启用 GitHub Pages
3. 再用 Pages 顶部调试面板逐项验证功能
