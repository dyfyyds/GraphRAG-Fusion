# RAG 智能问答系统 — Docker Compose 部署

基于 RAG（检索增强生成）架构的企业级智能问答平台，支持私有知识库管理、知识图谱构建、多路检索融合和流式 AI 对话。

## 系统架构

```
                    ┌─────────────────────────────────────┐
                    │              Nginx (:80)             │
                    │   静态文件 / 反向代理 / SSE 流式代理   │
                    └──────────┬──────────┬───────────────┘
                               │          │
                   ┌───────────┘          └────────────┐
                   ▼                                   ▼
          ┌────────────────┐                ┌──────────────────┐
          │  Frontend (Vue) │                │ Backend (FastAPI) │
          │   Nginx :80     │                │   Uvicorn :8080   │
          └────────────────┘                └────────┬─────────┘
                                                     │
                                    ┌────────────────┼────────────────┐
                                    ▼                ▼                ▼
                            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
                            │  MySQL :3306 │ │ Neo4j :7700/ │ │ ChromaDB     │
                            │   关系数据    │ │  :7687 图谱   │ │  :8000 向量库 │
                            └──────────────┘ └──────────────┘ └──────────────┘
```

## 核心功能

- **智能问答** — RAG 检索增强生成，三路检索（向量语义 + 知识图谱 + 关键词）融合，SSE 流式响应
- **知识库管理** — 文档上传（PDF / Word / TXT / Markdown）→ 自动解析 → 智能分块 → 向量化入库
- **知识图谱** — LLM 自动抽取实体与关系写入 Neo4j，D3.js 力导向图可视化，支持审核与手动编辑
- **用户管理** — RBAC 权限控制（管理员 / 普通用户），JWT 认证
- **系统配置** — LLM / Embedding / 检索参数在线配置，API Key 状态检测
- **工作台** — 数据统计概览、趋势图表、系统健康监控

## 目录结构

```
docker-em/
├── docker-compose.yml          # 服务编排（6 个核心服务 + 1 个测试服务）
├── .env.example                # 环境变量模板
├── .env                        # 环境变量（需从 .env.example 复制）
├── .gitignore
├── README.md
├── backend/
│   ├── Dockerfile              # Python 3.12 + FastAPI
│   ├── requirements.txt        # Python 依赖
│   ├── main.py                 # 应用入口
│   ├── app/
│   │   ├── api/                # API 路由（auth, qa, kb, graph, admin, config）
│   │   ├── core/               # 核心模块（LLM 客户端、图谱构建、运行时配置）
│   │   ├── models/             # SQLAlchemy 数据模型
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 业务逻辑层
│   │   └── db/                 # 数据库连接（MySQL、Neo4j、ChromaDB）
│   └── tests/                  # pytest 测试用例
├── frontend/
│   ├── Dockerfile              # 多阶段构建：Node 20 → Nginx
│   ├── nginx.conf              # SPA Nginx 配置
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── views/              # 页面组件
│       │   ├── admin/          # 管理后台（系统配置、知识图谱、用户管理）
│       │   ├── qa/             # 智能问答
│       │   └── kb/             # 知识库管理
│       ├── api/                # API 请求封装
│       ├── router/             # Vue Router 路由
│       └── stores/             # Pinia 状态管理
├── mysql/
│   └── init.sql                # 数据库初始化（建表 + 初始数据）
└── nginx/
    └── nginx.conf              # 入口反向代理（含 charset utf-8 响应头）
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.12) + Uvicorn |
| 前端框架 | Vue 3 + Element Plus + Vite |
| 关系数据库 | MySQL 8.0 (SQLAlchemy 2.0 async) |
| 图数据库 | Neo4j 5 Community |
| 向量数据库 | ChromaDB 1.0.7 |
| 大模型 | OpenAI 兼容 API（mimo-v2.5-pro） |
| Embedding | BAAI/bge-m3 (1024 维) |
| 部署 | Docker Compose + Nginx 反向代理 |

## 服务端口

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|------|----------|-----------|------|
| Nginx | 80 | 80 | 统一入口 |
| Backend | 8080 | 8080 | FastAPI REST API |
| MySQL | 3306 | 3306 | 关系数据库 |
| Neo4j HTTP | 7474 | 7700 | Neo4j Browser |
| Neo4j Bolt | 7687 | 7687 | 图数据库协议 |
| ChromaDB | 8000 | 8000 | 向量数据库 |

## 快速开始

### 1. 前置条件

- Docker >= 24.0
- Docker Compose >= 2.20
- 至少 4GB 可用内存

### 2. 克隆项目

```bash
git clone git@github.com:dyfyyds/GraphRAG-Fusion.git
cd docker-em
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入实际的 API Key 和密码：

```bash
# 必须修改的项
MYSQL_ROOT_PASSWORD=your_strong_root_password
MYSQL_PASSWORD=your_strong_user_password
NEO4J_AUTH=neo4j/your_strong_neo4j_password
NEO4J_PASSWORD=your_strong_neo4j_password
JWT_SECRET=your_jwt_secret_at_least_32_chars
LLM_API_KEY=your_llm_api_key
EMBEDDING_API_KEY=your_embedding_api_key
```

### 4. 构建并启动

```bash
# 首次启动（构建镜像，耗时较长）
docker compose up -d --build

# 查看启动日志
docker compose logs -f
```

### 5. 验证服务

```bash
docker compose ps
# 预期：所有服务 STATUS 为 healthy 或 running
```

### 6. 访问系统

| 地址 | 说明 |
|------|------|
| http://localhost | 前端页面 |
| http://localhost:8080/docs | API Swagger 文档 |
| http://localhost:7700 | Neo4j 控制台 |
| http://localhost:8000/docs | ChromaDB API |

### 7. 默认管理员

- 用户名: `admin`
- 密码: `admin123`

> 首次登录后请立即修改密码。

## 数据库连接

| 数据库 | 地址 | 用户名 | 密码 |
|--------|------|--------|------|
| MySQL | localhost:3306 | rag | 见 .env `MYSQL_PASSWORD` |
| Neo4j Bolt | localhost:7687 | neo4j | 见 .env `NEO4J_PASSWORD` |
| Neo4j HTTP | localhost:7700 | neo4j | 见 .env `NEO4J_PASSWORD` |
| ChromaDB | localhost:8000 | — | — |

## 常用命令

```bash
# 服务管理
docker compose ps                          # 查看所有服务状态
docker compose logs -f                     # 实时日志（所有服务）
docker compose logs -f backend             # 仅后端日志
docker compose down                        # 停止服务（保留数据）
docker compose down -v                     # 停止并清除所有数据

# 重建单个服务（代码更新后）
docker compose build backend
docker compose up -d backend

# 进入容器
docker compose exec backend bash
docker compose exec mysql mysql -u rag -p
docker compose exec neo4j cypher-shell -u neo4j -p <password>

# 数据备份
docker compose exec mysql mysqldump -u root -p rag_db > backup_$(date +%Y%m%d).sql

# 数据恢复
docker compose exec -T mysql mysql -u root -p rag_db < backup.sql

# 运行测试
docker compose --profile test run --rm test
```

## 健康检查

| 服务 | 检查方式 | 间隔 | 启动等待 |
|------|----------|------|----------|
| MySQL | `mysqladmin ping` | 10s | 30s |
| Neo4j | HTTP GET :7474 | 15s | 40s |
| ChromaDB | TCP :8000 | 10s | 30s |
| Backend | HTTP GET /api/health | 10s | 15s |
| Nginx | HTTP GET / | 10s | 5s |

## 服务依赖

```
mysql (healthy) ──┐
neo4j (healthy) ──┼──> backend (healthy) ──┬──> nginx
chromadb (healthy)┘                        │
frontend (started) ────────────────────────┘
```

## 注意事项

1. **首次启动** Neo4j 初始化较慢，需等待 healthcheck 通过后 backend 才会启动
2. **ChromaDB 版本** 固定为 1.0.7，跨大版本升级可能导致数据不兼容
3. **数据持久化** 所有数据存储在 Docker named volumes 中，`docker compose down`（不带 `-v`）不会丢失
4. **生产部署** 请务必修改所有默认密码和 JWT_SECRET
5. **字符编码** MySQL 使用 utf8mb4，Nginx 强制 UTF-8 响应头，确保中文正常显示
6. **文件上传** 存储在 `uploads` 数据卷中，容器内路径为 `/app/uploads`
7. **API 兼容** LLM 和 Embedding 使用 OpenAI 兼容接口，可替换为任意兼容服务

---

## 最近修复

### 2026-05-30 修复管理员后台历史记录显示问题

**问题描述**:
- 管理员后台看不到问答历史记录
- 登录不存在的用户显示"参数校验失败"而不是友好提示

**修复内容**:

1. **管理员后台历史记录**
   - 修改 `frontend/src/views/admin/AdminHistory.vue`
   - 直接使用 `/api/conversations/admin` 返回的数据，不再重复请求消息
   - 正确映射数据字段（question、answer、sources、feedback）

2. **登录错误提示优化**
   - 修改 `backend/app/middleware/exception_handler.py`
   - 增强验证错误处理器，提供更友好的错误消息
   - 当用户名或密码字段缺失时显示具体提示

3. **后端 API 数据验证**
   - 修改 `backend/app/schemas/conversations.py`
   - 将 `feedback` 字段类型改为 `int | None`，修复与数据库类型不匹配问题
   - 修复 Message 模型与数据库表结构不匹配问题

**部署方式**:
```bash
# 后端更新（无需重建镜像）
docker cp backend/app/middleware/exception_handler.py rag-backend:/app/app/middleware/
docker cp backend/app/schemas/conversations.py rag-backend:/app/app/schemas/
docker cp backend/app/models/message.py rag-backend:/app/app/models/
docker restart rag-backend

# 前端更新（无需重建镜像）
cd frontend && npm run build
docker cp dist/. rag-frontend:/usr/share/nginx/html/
docker restart rag-frontend
```

---

## 待改进事项 (TODO)

### P0 — 安全问题（必须修复）

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 1 | 文件上传路径穿越 | `backend/app/api/documents.py:40` | `file.filename` 未经清洗直接拼接路径，`../../etc/passwd.md` 可通过扩展名校验。需用 `secure_filename` 或生成 UUID 文件名 |
| 2 | 前端 `v-html` XSS 风险 | `frontend/.../MessageBubble.vue:5`, `Chat.vue:53` | Markdown 渲染结果直接用 `v-html` 输出，LLM 生成的 HTML 可执行脚本。需配置 DOMPurify 过滤 |
| 3 | 登录页展示演示账号 | `frontend/.../Login.vue:42-51` | `admin/admin123`、`user/user123` 可一键登录，生产环境需移除或用环境变量控制 |
| 4 | 管理员重置密码硬编码为 `123456` | `frontend/.../UserManage.vue:214` | 应弹窗让管理员输入新密码 |

### P1 — 后端性能与正确性

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 6 | 关键词搜索用 `LIKE '%query%'` 全表扫描 | `backend/app/core/rag_engine.py:186` | `chunks` 表无全文索引，数据量大时极慢。需加 MySQL FULLTEXT 索引并改用 `MATCH...AGAINST` |
| 7 | `admin_list_conversations` N+1 查询 | `backend/app/services/conversation_service.py:106-134` | 每条对话额外查 2 次消息表，分页 10 条 = 21 次查询。应改为单条 JOIN 查询 |
| 8 | 删除文档未清理 Neo4j 实体 | `backend/app/services/document_service.py` | ChromaDB 向量和 MySQL 记录已清理，但 Neo4j 中关联的实体和关系残留 |
| 9 | 注入检测规则重复定义 | `chat_service.py:13` 和 `rag_engine.py:37` | 两处 `INJECTION_PATTERNS` 完全相同，应抽取为共享工具模块 |
| 10 | LLM 流式重试逻辑与非流式不一致 | `backend/app/core/llm_client.py` | `chat` 用 tenacity 指数退避，`chat_stream` 手写 `while attempt < 3`，缺少退避策略 |
| 11 | 图谱检索每次都调 LLM 抽取关键词 | `backend/app/core/rag_engine.py:152-161` | 增加延迟和成本。简单查询可用正则或 NER 替代 |
| 12 | Config 缓存多 Worker 不一致 | `backend/app/services/config_service.py` | 模块级 `_cache` 在 4 Worker 进程中各自独立，一 Worker 更新配置后其他 Worker 不感知 |

### P2 — 前端质量

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 13 | API 调用分散在各组件中 | 多个 View 文件 | 除 `api/auth.js` 外无集中 API 模块，端点散落在 8+ 组件的 `<script setup>` 中。应抽取 `api/documents.js`、`api/chat.js` 等 |
| 14 | 空 `catch {}` 吞掉所有错误 | `Chat.vue`、`KnowledgeBase.vue`、`Dashboard.vue` 等 | 调试和排查问题极其困难。至少应 `console.error`，理想情况展示用户提示 |
| 15 | 历史页面 N+1 前端请求 | `AdminHistory.vue:206-229`、`UserHistory.vue:149-173` | 先拉全部对话，再逐条拉消息。应提供后端分页+消息批量查询接口 |
| 16 | 全局无错误边界 | `main.js` | 未配置 Vue `errorHandler`，组件渲染异常会导致整个应用白屏 |

### P3 — DevOps 与部署

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 17 | 缺少 `.dockerignore` | `backend/`、`frontend/` | `COPY . .` 会将 `__pycache__`、`node_modules`、`.git` 等打入镜像，增大体积 |
| 18 | 无数据库迁移工具 | 项目根目录 | 无 Alembic 等迁移框架，Schema 变更需手动执行 SQL 或重建数据库 |
| 19 | 容器无资源限制 | `docker-compose.yml` | 无 `mem_limit` / `deploy.resources.limits`，Neo4j 堆内存设为 1G 但容器层面无约束 |
| 20 | MySQL 健康检查暴露密码 | `docker-compose.yml:28` | `mysqladmin ping -p${MYSQL_ROOT_PASSWORD}` 在 `ps` 中可见明文密码 |
| 21 | 无 HTTPS / TLS | `nginx/nginx.conf` | 仅监听 80 端口，生产部署需 TLS 终端 |
| 22 | 无自动化数据备份 | 项目根目录 | README 有手动备份命令但无定时任务，应加 cron 或 Docker sidecar |

### P4 — 测试覆盖

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 23 | 无 Service 层集成测试 | `backend/tests/` | 仅覆盖工具函数，chat_service、document_service、graph_service 等 8 个核心服务无测试 |
| 24 | 无 API 端点测试 | `backend/tests/` | 仅 `test_api_health.py` 测试了健康检查，无 CRUD / 认证流程测试 |
| 25 | 无前端测试 | `frontend/` | 无 Vitest 单元测试、无 Cypress/Playwright E2E 测试 |
| 26 | `validate_file_content()` 从未被调用 | `backend/app/utils/file_utils.py` | 定义了 MIME 类型校验（python-magic）但上传流程中未使用 |

### P5 — 其他优化

| # | 问题 | 位置 | 说明 |
|---|------|------|------|
| 27 | 无接口限流 | 全局 | 尤其 chat 端点调用 LLM API，无 `slowapi` 等限流中间件，存在滥用风险 |
| 28 | JWT 无刷新机制 | 前端认证流程 | Token 24h 过期但无 refresh 流程，过期后直接跳登录页，用户体验差 |
| 29 | Logout 为空操作 | `backend/app/api/auth.py:18` | 仅返回成功消息，无服务端 Token 失效（黑名单），被盗 Token 在过期前仍有效 |
| 30 | 前端未使用 TypeScript | `frontend/` | 项目规模已不小，纯 JS 缺少类型检查，重构和协作易出错 |
| 31 | `system_config` 用 TEXT 存 JSON | `mysql/init.sql` | 应使用 MySQL JSON 列类型，支持 JSON 函数查询和校验 |
| 32 | Nginx 缺安全响应头 | `nginx/nginx.conf` | 无 `Content-Security-Policy`、`X-Frame-Options`、`X-Content-Type-Options` 等 |
