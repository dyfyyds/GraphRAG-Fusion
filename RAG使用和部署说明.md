# 基于RAG的企业级智能问答系统 — 使用和部署说明

> 项目版本：V1.0  
> 编制日期：2026年6月

---

## 目录

- [一、项目概述](#一项目概述)
  - [1.1 项目简介](#11-项目简介)
  - [1.2 核心功能](#12-核心功能)
  - [1.3 技术架构](#13-技术架构)
- [二、环境要求与依赖](#二环境要求与依赖)
  - [2.1 硬件要求](#21-硬件要求)
  - [2.2 软件要求](#22-软件要求)
  - [2.3 服务端口规划](#23-服务端口规划)
- [三、部署指南](#三部署指南)
  - [3.1 部署前准备](#31-部署前准备)
  - [3.2 环境变量配置](#32-环境变量配置)
  - [3.3 Docker Compose 部署](#33-docker-compose-部署)
  - [3.4 服务启动与验证](#34-服务启动与验证)
  - [3.5 开发模式部署](#35-开发模式部署)
- [四、系统使用说明](#四系统使用说明)
  - [4.1 登录系统](#41-登录系统)
  - [4.2 管理员功能](#42-管理员功能)
  - [4.3 普通用户功能](#43-普通用户功能)
- [五、运维管理](#五运维管理)
  - [5.1 常用运维命令](#51-常用运维命令)
  - [5.2 日志管理](#52-日志管理)
  - [5.3 数据备份与恢复](#53-数据备份与恢复)
  - [5.4 健康检查](#54-健康检查)
- [六、API 接口说明](#六api-接口说明)
- [七、常见问题与故障排除](#七常见问题与故障排除)
- [八、安全注意事项](#八安全注意事项)

---

## 一、项目概述

### 1.1 项目简介

本系统是一个面向企业用户的智能问答平台，基于 RAG（Retrieval-Augmented Generation，检索增强生成）架构，通过对接私有知识库，为企业提供精准、可靠的智能问答服务。系统支持多种文档格式的上传与解析，自动构建知识图谱，并通过三路检索（向量检索 + 图谱检索 + 关键词检索）融合策略，为用户提供高质量的回答，同时附带来源引用，确保回答的可追溯性。

### 1.2 核心功能

| 功能模块 | 功能说明 |
|---------|---------|
| 智能问答 | 基于 RAG 架构的三路检索融合，SSE 流式响应，支持多轮对话与上下文理解 |
| 知识库管理 | 支持 PDF、Word、TXT、Markdown 格式文档上传，自动解析、分块、向量化 |
| 知识图谱 | LLM 自动抽取实体与关系，3D 力导向图可视化，支持实体编辑与筛选 |
| 用户管理 | RBAC 权限控制，区分管理员与普通用户角色 |
| 系统配置 | 在线配置 LLM/Embedding 模型参数、检索策略、分块策略等 |
| 工作台仪表盘 | 数据统计、趋势图表、系统健康监控 |
| 问答历史 | 完整的对话记录与反馈管理 |

### 1.3 技术架构

系统采用前后端分离架构，通过 Docker Compose 编排 6 个核心服务：

| 服务 | 技术栈 | 职责 |
|------|--------|------|
| 前端 | Vue 3 + Element Plus + Vite | 用户界面与交互 |
| 后端 | FastAPI + Python 3.12 | API 服务与业务逻辑 |
| MySQL 8.0 | 关系型数据库 | 业务数据持久化 |
| Neo4j 5 | 图数据库 | 知识图谱存储与查询 |
| ChromaDB 1.0.7 | 向量数据库 | 文档向量存储与相似度检索 |
| Nginx | 反向代理 | 请求路由、负载均衡、SSE 代理 |

**请求流向：** 用户浏览器 → Nginx（端口 80）→ 前端容器（静态资源）/ 后端容器（API）→ MySQL（业务数据）+ Neo4j（图谱数据）+ ChromaDB（向量数据）。后端通过外部 API 调用 LLM（mimo-v2.5-pro）和 Embedding（Qwen3-Embedding-0.6B）服务完成推理。

---

## 二、环境要求与依赖

### 2.1 硬件要求

| 配置级别 | 处理器 | 内存 | 磁盘 |
|---------|--------|------|------|
| 最低配置 | 4 核 CPU | 8 GB | 40 GB SSD |
| 推荐配置 | 8 核 CPU | 16 GB | 100 GB SSD |

> Neo4j 建议分配至少 1.5 GB 堆内存，ChromaDB 需要一定的向量索引存储空间。

### 2.2 软件要求

| 软件 | 版本要求 | 用途 | 必要性 |
|------|---------|------|--------|
| Docker | ≥ 24.0 | 容器运行时 | 必需 |
| Docker Compose | ≥ 2.20 | 服务编排 | 必需 |
| Git | ≥ 2.40 | 源码获取 | 必需 |
| curl | 任意版本 | 健康检查 | 可选 |
| bash | 任意版本 | 批量上传脚本 | 可选 |

### 2.3 服务端口规划

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Nginx 反向代理 | 用户访问入口 |
| 3306 | MySQL 数据库 | 默认可不对外暴露 |
| 7700 | Neo4j Web 界面 | 图数据库管理界面 |
| 7687 | Neo4j Bolt 协议 | 后端连接 Neo4j |
| 8000 | ChromaDB API | 向量数据库服务 |
| 8080 | FastAPI 后端 | 后端 API 服务 |

> 所有端口均可通过 `.env` 文件自定义修改。生产环境建议仅暴露 80 端口。

---

## 三、部署指南

### 3.1 部署前准备

**步骤一：获取源代码**

```bash
git clone <仓库地址>
cd RAG/docker-em
```

**步骤二：确认 Docker 环境**

```bash
docker --version      # 需要 >= 24.0
docker compose version  # 需要 >= 2.20
```

**步骤三：准备 LLM 和 Embedding API 密钥**

系统需要外部 LLM 和 Embedding 服务的 API 密钥。默认配置使用：

- **LLM：** mimo-v2.5-pro（小米 MiMo）
- **Embedding：** Qwen3-Embedding-0.6B（SiliconFlow）

如需更换模型，请在 `.env` 文件中修改对应的 API 地址和密钥。

### 3.2 环境变量配置

项目根目录下提供 `.env.example` 模板文件。部署前需将其复制为 `.env` 并填入实际值：

```bash
cp .env.example .env
```

**`.env` 文件完整配置说明：**

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MYSQL_ROOT_PASSWORD` | rag_root_2024 | MySQL root 密码 |
| `MYSQL_DATABASE` | rag_db | 数据库名 |
| `MYSQL_USER` | rag | 应用数据库用户 |
| `MYSQL_PASSWORD` | rag_pwd_2024 | 应用数据库密码 |
| `MYSQL_PORT` | 3306 | MySQL 端口 |
| `NEO4J_AUTH` | neo4j/neo4j_pwd_2024 | Neo4j 认证（格式：用户/密码） |
| `NEO4J_USER` | neo4j | Neo4j 用户名 |
| `NEO4J_PASSWORD` | neo4j_pwd_2024 | Neo4j 密码 |
| `NEO4J_HTTP_PORT` | 7700 | Neo4j HTTP 端口 |
| `NEO4J_BOLT_PORT` | 7687 | Neo4j Bolt 端口 |
| `CHROMA_PORT` | 8000 | ChromaDB 端口 |
| `BACKEND_PORT` | 8080 | 后端服务端口 |
| `LLM_API_KEY` | **（必填）** | LLM API 密钥 |
| `LLM_API_URL` | https://token-plan-cn.xiaomimimo.com/v1/chat/completions | LLM API 地址 |
| `LLM_MODEL` | mimo-v2.5-pro | LLM 模型名称 |
| `EMBEDDING_API_KEY` | **（必填）** | Embedding API 密钥 |
| `EMBEDDING_API_URL` | https://api.siliconflow.cn/v1 | Embedding API 地址 |
| `EMBEDDING_MODEL` | Qwen/Qwen3-Embedding-0.6B | Embedding 模型名称 |
| `EMBEDDING_DIM` | 1024 | 向量维度 |
| `LLM_TIMEOUT` | 120 | LLM 调用超时（秒） |
| `EMBEDDING_TIMEOUT` | 30 | Embedding 调用超时（秒） |
| `NGINX_PORT` | 80 | Nginx 对外端口 |
| `JWT_SECRET` | **（必填，≥32字符）** | JWT 签名密钥 |

**安全提示：**

- 生产环境务必修改所有默认密码
- `JWT_SECRET` 建议使用随机生成的长字符串
- `LLM_API_KEY` 和 `EMBEDDING_API_KEY` 为必填项，否则系统无法进行 AI 推理
- `.env` 文件已加入 `.gitignore`，不会被提交到版本库

### 3.3 Docker Compose 部署

**一键启动所有服务：**

```bash
docker compose up -d --build
```

**启动过程说明：**

1. Docker 首次运行会拉取基础镜像（MySQL 8.0、Neo4j 5、ChromaDB 1.0.7、Python 3.12、Node 20、Nginx Alpine）
2. 构建后端镜像：安装 Python 依赖（使用阿里云 PyPI 镜像加速）
3. 构建前端镜像：Node 20 编译 Vue 3 项目 → Nginx Alpine 托管静态文件
4. 按依赖顺序启动服务：MySQL → Neo4j → ChromaDB → Backend → Frontend → Nginx
5. 各服务健康检查通过后，Nginx 开始接收外部请求

> 首次构建大约需要 5-10 分钟（取决于网络速度和机器性能）。

**查看服务状态：**

```bash
docker compose ps
```

**预期输出**（所有服务应为 running/healthy 状态）：

```
NAME            STATUS          PORTS
rag-mysql       running (healthy)   0.0.0.0:3306->3306/tcp
rag-neo4j       running (healthy)   0.0.0.0:7700->7474/tcp
rag-chromadb    running (healthy)   0.0.0.0:8000->8000/tcp
rag-backend     running (healthy)   0.0.0.0:8080->8080/tcp
rag-frontend    running             80/tcp
rag-nginx       running (healthy)   0.0.0.0:80->80/tcp
```

### 3.4 服务启动与验证

启动完成后，按以下顺序验证各组件：

| 步骤 | 验证项 | 操作 | 预期结果 |
|------|--------|------|---------|
| 1 | 系统首页 | 浏览器访问 http://localhost | 应显示登录页面 |
| 2 | 健康检查 | `curl http://localhost/api/health` | `{"status":"ok"}` |
| 3 | 登录 | 用户名: admin, 密码: admin123 | 应进入管理员仪表盘 |
| 4 | API 文档 | http://localhost/docs | 应显示 Swagger UI |
| 5 | Neo4j 界面 | http://localhost:7700 | 应显示 Neo4j Browser |

### 3.5 开发模式部署

如需本地开发调试，可分别启动前后端服务：

**后端开发模式：**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

**前端开发模式：**

```bash
cd frontend
npm install
npm run dev
```

> 开发模式下，Vite 开发服务器运行在 5173 端口，并自动代理 `/api` 请求到后端 8080 端口。前端支持热模块替换（HMR），修改代码后浏览器自动刷新。

---

## 四、系统使用说明

### 4.1 登录系统

访问系统首页（http://localhost），自动跳转到登录页面。

**默认管理员账户：**

- 用户名：`admin`
- 密码：`admin123`

**登录后跳转规则：**

- 管理员 → 管理员仪表盘（`/admin`）
- 普通用户 → 智能问答页面（`/`）

### 4.2 管理员功能

#### 4.2.1 工作台仪表盘

管理员登录后默认进入工作台，可查看：

- 文档总数、用户总数、对话总数、消息总数
- 文档上传趋势图（按日/周/月统计）
- 系统健康状态（各服务连接状态）
- 最近活动记录

#### 4.2.2 知识库管理

**功能说明：**

- **文档上传：** 支持 PDF、Word（.docx）、TXT、Markdown 格式，单文件最大 50MB
- **批量上传：** 支持一次选择多个文件（最多 10 个）
- **文档列表：** 查看所有已上传文档的状态（待处理/解析中/构建图谱中/完成/失败）
- **文档详情：** 查看文档的分块数量、解析状态、错误信息
- **删除文档：** 删除文档及其关联的向量数据和图谱数据
- **SSE 实时推送：** 上传过程中实时显示解析进度

**文档处理流程：**

1. 上传文档 → 状态设为 `pending`
2. 自动解析文档内容（PDF/Word/TXT/MD）
3. 文本分块（默认 512 字符/块，50 字符重叠）
4. 向量化并存入 ChromaDB
5. LLM 自动抽取实体与关系，构建知识图谱
6. 状态更新为 `completed`

#### 4.2.3 知识图谱

- **3D 可视化：** 基于 Three.js 的力导向图展示实体与关系
- **实体筛选：** 按实体类型（组织/法规/政策/文件等）筛选显示
- **关系筛选：** 按关系类型（发布/引用/规范/约束等）筛选显示
- **实体详情：** 点击节点查看实体属性与关联关系
- **图谱导入：** 支持从 JSON 文件批量导入实体和关系

#### 4.2.4 用户管理

- 用户列表：查看所有注册用户（用户名、角色、状态、注册时间）
- 创建用户：添加新用户并分配角色（管理员/普通用户）
- 启用/禁用：控制用户账户状态
- 角色管理：修改用户角色权限

#### 4.2.5 系统配置

- **LLM 模型配置：** 设置模型名称、API 地址、温度、top_p、最大 token 数
- **Embedding 模型配置：** 设置模型名称、API 地址、向量维度
- **检索配置：** 调整 top_k（返回数量）、相似度阈值、向量/图谱权重
- **知识图谱配置：** 设置实体类型、关系类型
- **分块配置：** 调整分块大小和重叠字符数
- **上传限制：** 设置最大文件大小和单次上传数量

#### 4.2.6 问答历史管理

- 查看所有用户的对话记录
- 按用户、时间、关键词筛选对话
- 查看每条消息的引用来源
- 查看用户反馈（好评/差评）

### 4.3 普通用户功能

#### 4.3.1 智能问答

- **新建对话：** 点击新建按钮创建新的对话会话
- **发送消息：** 在输入框输入问题，支持 Shift+Enter 换行
- **流式响应：** 回答以 SSE 流式方式逐步展示，支持实时查看
- **来源引用：** 每条回答附带引用的文档来源卡片，点击可展开查看原文
- **多轮对话：** 系统自动携带上下文，支持追问和深入讨论
- **反馈评价：** 对回答进行好评/差评评价，支持文字反馈

#### 4.3.2 问答历史

- 对话列表：查看个人所有历史对话
- 对话搜索：按关键词搜索历史对话
- 删除对话：删除不需要的对话记录

---

## 五、运维管理

### 5.1 常用运维命令

| 操作 | 命令 |
|------|------|
| 启动所有服务 | `docker compose up -d` |
| 停止所有服务 | `docker compose down` |
| 重启所有服务 | `docker compose restart` |
| 重新构建并启动 | `docker compose up -d --build` |
| 查看服务状态 | `docker compose ps` |
| 查看实时日志 | `docker compose logs -f` |
| 查看特定服务日志 | `docker compose logs -f backend` |
| 进入后端容器 | `docker compose exec backend bash` |
| 进入 MySQL | `docker compose exec mysql mysql -u rag -p` |
| 进入 Neo4j | `docker compose exec neo4j cypher-shell -u neo4j` |
| 查看后端健康 | `curl http://localhost/api/health` |
| 运行测试 | `docker compose --profile test run --rm test` |

### 5.2 日志管理

**各服务日志存储位置：**

- **Nginx 日志：** 容器内 `/var/log/nginx/access.log` 和 `error.log`
- **后端日志：** 通过 `docker compose logs` 查看，支持结构化日志格式
- **MySQL 日志：** 容器内 `/var/log/mysql/`
- **Neo4j 日志：** 通过 docker volume `neo4j-logs` 挂载到宿主机

**定期清理日志：**

```bash
docker compose logs --tail=1000 backend > backend.log
```

### 5.3 数据备份与恢复

**MySQL 数据库备份：**

```bash
docker compose exec mysql mysqldump -u root -p rag_db > backup_$(date +%Y%m%d).sql
```

**MySQL 数据库恢复：**

```bash
docker compose exec -T mysql mysql -u root -p rag_db < backup.sql
```

**Docker 卷备份：**

```bash
# 备份所有数据卷
docker run --rm -v rag-mysql-data:/data -v $(pwd):/backup alpine tar czf /backup/mysql-data.tar.gz /data
docker run --rm -v rag-neo4j-data:/data -v $(pwd):/backup alpine tar czf /backup/neo4j-data.tar.gz /data
docker run --rm -v rag-chroma-data:/data -v $(pwd):/backup alpine tar czf /backup/chroma-data.tar.gz /data
```

### 5.4 健康检查

系统内置健康检查机制，各服务启动后自动进行：

| 服务 | 检查方式 | 检查间隔 | 启动等待 |
|------|---------|---------|---------|
| rag-mysql | `mysqladmin ping` | 10s | 30s |
| rag-neo4j | `wget http://localhost:7474` | 15s | 40s |
| rag-chromadb | TCP 端口检测 8000 | 10s | 30s |
| rag-backend | `curl http://localhost:8080/api/health` | 10s | 15s |
| rag-nginx | `curl http://localhost:80` | 10s | 5s |

**服务依赖链：** MySQL/Neo4j/ChromaDB → Backend → Nginx（只有上游服务健康检查通过后，下游服务才会启动）

---

## 六、API 接口说明

系统提供 RESTful API，完整文档可通过 Swagger UI 访问：http://localhost/docs

所有 API 以 `/api/` 为前缀，除登录、注册、健康检查外，均需携带 JWT Token（Bearer 认证）。

| 方法 | 路径 | 说明 | 认证 | 备注 |
|------|------|------|------|------|
| POST | `/api/auth/login` | 用户登录 | 否 | 返回 access_token |
| POST | `/api/auth/register` | 用户注册 | 否 | 创建新用户 |
| GET | `/api/health` | 健康检查 | 否 | 返回 `{"status":"ok"}` |
| GET | `/api/users/me` | 获取当前用户信息 | 是 | 返回用户详情 |
| GET | `/api/users` | 用户列表（管理员） | 是 | 分页返回用户列表 |
| POST | `/api/users` | 创建用户（管理员） | 是 | 创建新用户 |
| PUT | `/api/users/{id}` | 更新用户 | 是 | 修改用户信息 |
| DELETE | `/api/users/{id}` | 删除用户 | 是 | 删除指定用户 |
| POST | `/api/documents/upload` | 上传文档 | 是 | 支持 PDF/DOCX/TXT/MD |
| GET | `/api/documents` | 文档列表 | 是 | 分页返回文档列表 |
| GET | `/api/documents/{id}` | 文档详情 | 是 | 返回文档详情 |
| DELETE | `/api/documents/{id}` | 删除文档 | 是 | 删除文档及关联数据 |
| GET | `/api/documents/events` | SSE 事件流 | 是 | 实时推送处理进度 |
| POST | `/api/chat` | 发送问答（SSE） | 是 | 流式返回回答 |
| GET | `/api/conversations` | 对话列表 | 是 | 返回用户的对话列表 |
| GET | `/api/conversations/{id}` | 对话详情 | 是 | 返回对话及消息 |
| DELETE | `/api/conversations/{id}` | 删除对话 | 是 | 删除对话记录 |
| POST | `/api/conversations/{id}/feedback` | 消息反馈 | 是 | 好评/差评评价 |
| GET | `/api/graph/entities` | 实体列表 | 是 | 支持类型筛选 |
| GET | `/api/graph/relations` | 关系列表 | 是 | 支持类型筛选 |
| GET | `/api/graph/stats` | 图谱统计 | 是 | 实体/关系统计 |
| POST | `/api/graph/import` | 导入图谱数据 | 是 | JSON 批量导入 |
| GET | `/api/config` | 获取系统配置 | 是 | 返回所有配置项 |
| PUT | `/api/config` | 更新系统配置 | 是 | 修改配置项 |
| GET | `/api/dashboard/stats` | 仪表盘统计 | 是 | 管理员数据统计 |

---

## 七、常见问题与故障排除

| 问题 | 解决方案 |
|------|---------|
| `docker compose up` 报错端口占用 | 检查端口占用：`netstat -tlnp \| grep <端口号>`，修改 `.env` 中对应端口，或停止占用端口的进程 |
| 后端启动失败，MySQL 连接拒绝 | 确认 MySQL 容器已健康启动：`docker compose ps`，检查 `.env` 中 `MYSQL_PASSWORD` 是否正确，等待 MySQL 健康检查通过后再启动后端 |
| Neo4j 连接失败 | 确认 Neo4j 容器已启动：`docker compose ps neo4j`，检查 `NEO4J_AUTH` 格式是否为 `用户名/密码`，访问 http://localhost:7700 验证 Neo4j 界面 |
| ChromaDB 连接超时 | 确认 ChromaDB 容器已启动：`docker compose ps chromadb`，检查端口 8000 是否被占用 |
| 文档上传后状态一直为 pending | 检查后端日志：`docker compose logs backend`，确认 LLM API 密钥有效且余额充足，检查网络是否能访问 LLM API 地址 |
| 问答没有返回结果 | 确认已上传文档并解析完成（状态为 `completed`），检查 Embedding API 密钥是否有效，检查系统配置中的检索参数是否合理 |
| Nginx 返回 502 Bad Gateway | 后端服务可能未启动完成，等待健康检查通过；检查后端日志排查启动错误；尝试重启：`docker compose restart nginx backend` |
| 前端页面空白 | 清除浏览器缓存后刷新，检查前端容器是否正常运行：`docker compose ps frontend`，检查 Nginx 配置是否正确 |
| Neo4j Browser 无法访问 | Neo4j 5 使用端口 7474（映射到宿主机 7700），确认访问地址为 http://localhost:7700 |
| 数据卷占用大量磁盘空间 | 定期清理旧数据：`docker volume prune`，备份后删除不需要的卷，Neo4j 日志卷可定期清理 |

---

## 八、安全注意事项

| 安全项 | 措施说明 |
|--------|---------|
| 密码安全 | 生产环境务必修改所有默认密码（MySQL root、应用用户、Neo4j、JWT_SECRET） |
| API 密钥保护 | `LLM_API_KEY` 和 `EMBEDDING_API_KEY` 属于敏感信息，切勿提交到代码仓库 |
| 端口暴露 | 生产环境仅暴露 Nginx 端口（80/443），数据库端口不对外暴露 |
| HTTPS | 生产环境建议在 Nginx 前添加 SSL 终止（如使用 Let's Encrypt） |
| 文件上传 | 系统限制上传文件大小为 50MB，支持 PDF/DOCX/TXT/MD 格式 |
| JWT 认证 | Token 有效期为 24 小时，过期后需重新登录 |
| RBAC 权限 | 普通用户无法访问管理员功能，前端路由守卫和后端中间件双重校验 |
| CORS 配置 | 当前仅允许 localhost 和 127.0.0.1 的跨域请求 |
| 数据备份 | 建议定期备份 MySQL 和 Neo4j 数据，防止数据丢失 |
| 日志审计 | 系统记录所有 API 请求日志，便于安全审计和问题排查 |

---

*— 文档结束 —*
