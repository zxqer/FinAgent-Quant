# 使用官方轻量级 Python 3.12 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统级依赖 (gRPC 和 ChromaDB 编译所需)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# 安装 Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# 仅复制依赖文件，利用 Docker 缓存加速构建
COPY pyproject.toml poetry.lock ./

# 安装 Python 依赖库
RUN poetry install --no-interaction --no-ansi --no-root

# 复制项目源代码
COPY . .

# 暴露可能需要的端口 (如果有 REST API 需求)
# EXPOSE 8000

# 启动入口点
CMD ["python", "main.py"]