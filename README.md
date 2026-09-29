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
  ├─ 检索技能库 → 命中？ ── 是 → 直接复用（复用次数 +1）
  └─ 否 → 检索教训注入 prompt → ReAct 循环解决
              └─ 自我评估（LLM-as-judge）判断真伪
                   ├─ 成功 → 提炼技能入库
                   └─ 失败 → 提炼教训入库
```

## 技术栈

- **ReAct 循环**：想一步 → 调工具 → 看结果，多步推理
- **反思提炼**：角色切换让 LLM 复盘轨迹，抽取技能/教训
- **自我评估**：`LLM-as-judge` 判断「是否真的成功」
- **检索（RAG）**：字符 n-gram + 余弦相似度 + 阈值 + name/description 双匹配
- **Redis**：技能库用 hash（天然查重），记忆库用 list（只追加）
- **FastAPI**：RESTful 接口；**MCP**：工具暴露给任意 MCP 客户端
- **大模型**：DeepSeek（OpenAI 兼容接口）+ 结构化输出 + 防御性解析

## 关键技术决策

1. **为什么用「接口 + 可替换实现」**：`SkillStore` 抽象出 `save/list_all/update`，从 JSON 文件换成 Redis 只改 `main.py` 两行，业务逻辑零改动。
2. **为什么技能库用 hash 而非 list**：list 只能追加，无法按名去重和更新；hash 的 `hset` 同名覆盖天然查重，更新就是再 `hset` 一次。
3. **为什么需要 LLM-as-judge**：光看「有没有 Final Answer」无法判断成败——模型会「优雅地失败」（老实说「我没有这个工具」就交差）。所以要靠模型的判断力鉴别真伪。
4. **字符 n-gram 的局限**：它只比字面、不比语义，「把文本反转」和 `reverse-text` 字面零重叠就会 miss。这正是生产环境用真实 embedding 模型的原因。

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

## API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/solve` | POST | 提交任务，走完整进化链路，返回 `method`（`solved` / `reused_skill` / `failed`） |
| `/skills` | GET | 查看技能库 |
| `/memories` | GET | 查看经验记忆 |

## 已知局限 / 未来方向

- 检索用字符 n-gram，中文↔英文存在**语义鸿沟** → 未来换真实 embedding 模型
- 失败判定依赖 LLM 裁判，存在概率性
- 技能按名字查重，同义不同名（如 `reverse-text` vs `reverse-string`）不会合并
