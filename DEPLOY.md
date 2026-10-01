# 部署指南

把 RetroAgent 部署成一个公开可访问的 Web 服务。这里以 **Render**（免费、无需绑卡、直连 GitHub）为例，Railway / Fly.io 流程类似，用的是同一套文件。

## 0. 已准备好的东西

| 文件 | 作用 |
|------|------|
| `Dockerfile` | 容器化（python 3.10-slim） |
| `requirements-deploy.txt` | 精简依赖（不装 paddle / sentence-transformers，镜像小、构建快） |
| `.dockerignore` | 排除 `.env` / `venv` 等，避免把密钥打进镜像 |
| `app/main.py` 的 `/health` | 平台探活接口 |
| `REDIS_URL` 支持 | 连接托管 Redis |

> 部署版用 `EMBEDDING_BACKEND=ngram`（零依赖）和 `OCR_BACKEND=dummy`（不识别图片），
> 因为真实语义模型和 OCR 引擎太重、免费实例装不下。本地开发仍可用完整版。

## 1. 准备一个托管 Redis（拿连接串）

免费推荐 **Upstash**（https://upstash.com）：
1. 注册 → 建一个 Redis 数据库（选免费档）
2. 复制连接串，形如 `rediss://default:xxxx@xxx.upstash.io:6379`

（**Redis Cloud** 的免费档同理，形如 `redis://default:xxxx@xxx:xxx`）

## 2. 把代码推到 GitHub

```bash
git add -A
git commit -m "部署准备"
git push origin main
```

## 3. 在 Render 上部署

1. 打开 https://render.com 注册（直接用 GitHub 账号登录）
2. 点 **New → Web Service**，选择 `kitfor11/RetroAgent` 仓库
3. Render 会自动识别 `Dockerfile`，直接点创建
4. 在 **Environment** 里填两个环境变量：
   - `DEEPSEEK_API_KEY` = 你的 DeepSeek key
   - `REDIS_URL` = 第 1 步拿到的连接串
5. 点 **Deploy**，等构建完成（几分钟）

部署完会得到一个 `https://xxx.onrender.com` 地址。

## 4. 验证

- 浏览器打开 `https://xxx.onrender.com/health`，看到 `{"status":"ok"}` 就成功了
- 接口文档在 `https://xxx.onrender.com/docs`（FastAPI 自带 Swagger，可直接在上面试 `/solve`）

## 环境变量清单

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek 的 key |
| `REDIS_URL` | 是 | 托管 Redis 连接串 |
| `EMBEDDING_BACKEND` | 否 | 默认 ngram（Dockerfile 已设） |
| `OCR_BACKEND` | 否 | 默认 dummy（Dockerfile 已设） |
| `PORT` | 否 | 平台自动注入，Dockerfile 已处理 |

## 已知限制

- 免费实例空闲 15 分钟会休眠，下次请求会冷启动（等几秒到几十秒）。
- 文档 RAG（`/index`、`/ask`）默认没有文档：镜像里的 `demo_files` 是空的，要演示得先往沙盒放文件（后续可加一个上传接口）。
- `chroma_db` 存在容器磁盘上，重启会清空（免费实例磁盘是临时的）。
