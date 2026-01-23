FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖 (用于 matplotlib 和 curl)
RUN apt-get update && apt-get install -y \
    fonts-noto-cjk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖配置
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# 复制源码
COPY . .

# 暴露端口
EXPOSE 8501

# 启动命令
CMD ["streamlit", "run", "web/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
