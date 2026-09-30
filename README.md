# EvoAgent — 自我进化型 AI Agent

一个「越用越强」的文本处理 Agent：完成任务后自动提炼成**可复用技能**，失败后自动记住**教训**，下次遇到同类任务直接复用经验、避开旧坑。

> 传统 Agent 每次任务都从零思考。EvoAgent 的核心是给 Agent 加了**记忆**——既记「怎么做对的」，也记「怎么做错的」。

## 核心机制：双进化

| 机制 | 触发 | 作用 |
|------|------|------|
| **技能库**（Skill Library） | 任务**成功** | 提炼成技能，同类任务直接复用（`reused_skill`） |
| **经验记忆**（Long-term Memory） | 任务**失败** | 提炼成教训，下次注入 prompt 主动避坑 |

完整流程：

```
提交任务
  ├─ 检索技能库 → 命中？ ── 是 → 技能作为「参考做法」注入，模型结合参考生成（RAG）
  └─ 否 → 检索教训注入 prompt → ReAct 循环解决（每步 Thought = CoT）
              └─ 自我评估（LLM-as-judge）判断真伪
                   ├─ 成功 → 提炼技能入库
                   └─ 失败 → 提炼教训入库
```

## 技术栈

- **ReAct 循环**：想一步 → 调工具 → 看结果，多步推理；每步显式输出 `Thought:`（**CoT 思维链**）
- **RAG（增强生成）**：检索技能/教训 → 注入 prompt → 结合参考生成，而不是照抄
- **反思提炼**：角色切换让 LLM 复盘轨迹，抽取技能/教训
- **自我评估**：`LLM-as-judge` 判断「是否真的成功」
- **向量检索**：余弦相似度 + 阈值；向量化可切换（字符 n-gram / 真实语义模型）
- **文件工具 + 沙盒**：list / read / mkdir / move 真实文件操作，全部限制在沙盒目录内
- **OCR（多模态）**：PaddleOCR 看图识字，让文件整理从「按扩展名」升级到「按内容」
- **文档 RAG（Chroma 向量库）**：切片 → 向量化 → 检索 top-k → 带引用回答；图片经 OCR 也能入库；既暴露成 `/ask` 接口，也作为 `search_docs` 工具给 Agent 用
- **Redis**：技能库用 hash（天然查重），记忆库用 list（只追加）
- **FastAPI**：RESTful 接口；**MCP**：工具暴露给任意 MCP 客户端
- **大模型**：DeepSeek（OpenAI 兼容接口）+ 结构化输出 + 防御性解析（含 stop 序列防「脑补」）

## 关键技术决策

1. **为什么用「接口 + 可替换实现」**：`SkillStore` 抽象出 `save/list_all/update`，从 JSON 文件换成 Redis 只改 `main.py` 两行，业务逻辑零改动。
2. **为什么技能库用 hash 而非 list**：list 只能追加，无法按名去重和更新；hash 的 `hset` 同名覆盖天然查重，更新就是再 `hset` 一次。
3. **为什么需要 LLM-as-judge**：光看「有没有 Final Answer」无法判断成败——模型会「优雅地失败」（老实说「我没有这个工具」就交差）。所以要靠模型的判断力鉴别真伪。
4. **为什么 embedding 也要「接口 + 可替换实现」**：字符 n-gram 只比字面、不比语义，中文↔英文会 miss。所以把向量化抽象成 `Embedder` 接口，n-gram 和真实语义模型都能插拔，通过 `EMBEDDING_BACKEND` 一键切换。
5. **为什么 ReAct 要加 `stop=["Observation:"]`**：纯文本 ReAct 的经典坑——模型会「体贴地」把 Observation 也自己编出来，工具根本没被调用（演示时真的抓到过一次，还编出了 8 个不存在的文件）。stop 序列在模型刚想写「Observation:」时截断，逼它交棒给真实工具。
6. **为什么 OCR 和 Chroma 能共存（protobuf 版本冲突）**：paddle 2.6 的生成代码是 protoc 3.x 产的（要求 protobuf ≤3.20），而 chromadb 要求 protobuf 7.x，两者版本要求没有交集。解法：锁 protobuf 7.x 给 chromadb，再设 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python`（纯 Python 实现兼容老生成代码）；开关放在 `config.py` 最顶部，必须在任何 protobuf 导入之前设置。

## 项目结构

```
app/
├── agent/
│   ├── react_loop.py   # ReAct 循环（想→做→看）
│   ├── reflect.py      # 反思：提炼技能 / 教训 / 裁判
│   ├── tools.py        # 工具注册表
│   └── agent.py        # 进化主链路
├── skills/             # 技能库：模型 / 存储 / 检索 / 向量化
├── memory/             # 记忆库：存储 / 检索
├── multimodal/         # 多模态：OCR（看图识字）
│   └── ocr.py          # OCR 引擎（接口 + PaddleOCR + 降级占位）
├── rag/                # 文档 RAG：切片 / 向量库 / 索引 / 问答
│   ├── chunker.py      # 切片器（固定长度 + overlap）
│   ├── store.py        # Chroma 向量库封装（存 / 检索 / 持久化）
│   ├── indexer.py      # 索引器（文本直读，图片走 OCR）
│   └── qa.py           # 问答（检索 → 增强 → 生成，带引用）
├── llm.py              # LLM 调用封装
├── config.py           # 环境变量配置
├── main.py             # FastAPI 入口
└── mcp_server.py       # MCP server
```

## 快速开始

1. 安装依赖：`pip install -r requirements.txt`
2. 配置环境：复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`
3. 启动 Redis（本地 `6379` 端口需有 Redis 运行）
4. 启动服务：`uvicorn app.main:app --reload`
5. 打开 `http://127.0.0.1:8000/docs` 测试

**跑演示**（会真实调用 DeepSeek）：
- 完整进化闭环（解决→复用→记教训→跨语言复用）：`venv/Scripts/python tests/demo_full.py`
- 文件整理助手（真实文件工具 + CoT 思维链）：`venv/Scripts/python tests/demo_files.py`
- OCR 文件整理（看图识字、按内容归档）：`venv/Scripts/python tests/demo_ocr.py`
- 文档 RAG 问答（Chroma 向量库 + 带引用回答，含图片 OCR 入库）：`venv/Scripts/python tests/demo_rag.py`
- Agent 调用文档检索工具（`search_docs`，自己查知识库回答）：`venv/Scripts/python tests/demo_agent_search.py`

**跑单元测试**（不联网、不调 LLM，秒级跑完）：
- `venv/Scripts/python -m pytest tests -q`
- 覆盖：切片器、n-gram 向量化 / 余弦相似度、技能 / 记忆检索、沙盒安全 + 字符串工具

> **可选：启用真实语义检索**。默认用字符 n-gram（零依赖）。要解决中文↔英文语义鸿沟，执行 `pip install sentence-transformers`，再把 `.env` 里的 `EMBEDDING_BACKEND` 改为 `sentence_transformers`（首次运行会下载约 120MB 模型）。验证效果跑 `venv/Scripts/python tests/verify_embedding.py`。

> **可选：启用 OCR**。文件整理要「看图识字」需 `pip install paddleocr==2.7.3 paddlepaddle==2.6.2`（首次运行下载约 15MB 模型；注意 numpy 要锁 1.26.4，见 requirements.txt）。验证跑 `venv/Scripts/python tests/verify_ocr.py`。

## API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/solve` | POST | 提交任务，走完整进化链路，返回 `method`（`solved` / `reused_skill` / `failed`） |
| `/skills` | GET | 查看技能库 |
| `/memories` | GET | 查看经验记忆 |
| `/index` | POST | 把沙盒文件索引进文档向量库（先清空再全量索引） |
| `/ask` | POST | 文档问答：检索相关片段，带引用来源回答 |

## 部署

容器化部署所需的文件已备好，步骤见 [DEPLOY.md](DEPLOY.md)：
- `Dockerfile` + `.dockerignore` + `requirements-deploy.txt`（精简依赖，不装 paddle/大模型）
- `/health` 健康检查接口
- 支持托管 Redis（`REDIS_URL` 连接串，如 Upstash/Redis Cloud）

一句话流程：注册托管 Redis 拿 `REDIS_URL` → 把代码 push 到 GitHub → 平台（Render/Railway）连仓库部署 → 填 `DEEPSEEK_API_KEY`、`REDIS_URL` 两个环境变量。

## 已知局限 / 未来方向

- 默认检索仍用字符 n-gram，中文↔英文有**语义鸿沟**（可设 `EMBEDDING_BACKEND=sentence_transformers` 换真实模型解决）
- 失败判定依赖 LLM 裁判，存在概率性
- 技能按名字查重，同义不同名（如 `reverse-text` vs `reverse-string`）不会合并
- 文档向量库是「快照」：文件改动后需重新 `/index` 才会生效（`search_docs` 工具也只懒建一次）
