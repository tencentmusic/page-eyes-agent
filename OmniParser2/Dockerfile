# 使用官方Python 3.12镜像作为基础镜像
FROM python:3.12

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 设置工作目录
WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list.d/debian.sources
# 安装必要的系统依赖和uv
RUN apt-get update && apt-get install -y \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libfontconfig1 \
    libxcb1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# 复制依赖文件（包括lockfile）
COPY pyproject.toml uv.lock ./

# 使用uv安装Python依赖
RUN uv sync

# 创建权重目录
RUN mkdir -p model/weights/icon_detect model/weights/icon_caption_florence

# 下载HuggingFace模型文件（打包进镜像）
RUN uv run huggingface-cli download microsoft/OmniParser-v2.0 \
        icon_detect/train_args.yaml \
        icon_detect/model.pt \
        icon_detect/model.yaml \
        icon_caption/config.json \
        icon_caption/generation_config.json \
        icon_caption/model.safetensors \
        --local-dir model/weights && \
    mv model/weights/icon_caption/* model/weights/icon_caption_florence/ && \
    rm -rf model/weights/icon_caption

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uv", "run", "python", "main.py"]
