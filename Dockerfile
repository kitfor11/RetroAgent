# RetroAgent 部署镜像（精简版：不装 paddle/大模型，OCR 用 dummy、嵌入用 ngram）
FROM python:3.10-slim

WORKDIR /app

# chromadb 的依赖 onnxruntime 在 slim 镜像里常缺 libgomp1，先装上避免运行时报错
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先拷依赖再装：requirements 不变时能命中 Docker 层缓存，重复构建快
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# 再拷代码和前端静态文件（放后面，代码改动不会触发重装依赖）
COPY app ./app
COPY static ./static

# 部署默认用零依赖的 ngram 嵌入 + dummy OCR（可在平台环境变量里覆盖）
ENV OCR_BACKEND=dummy EMBEDDING_BACKEND=ngram

EXPOSE 8000

# ${PORT:-8000}：平台（Render/Railway）会注入 PORT，本地构建默认 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
