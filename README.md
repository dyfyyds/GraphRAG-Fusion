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
git clone <repository-url>
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
