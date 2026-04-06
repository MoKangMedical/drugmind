FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 环境变量
ENV MIMO_BASE_URL=https://api.xiaomimimo.com/v1
ENV MIMO_MODEL=mimo-v2-pro

EXPOSE 8096

CMD ["python", "main.py", "serve", "--port", "8096"]
