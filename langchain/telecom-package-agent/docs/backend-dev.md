# 后端开发文档

本文档说明如何配置、启动和开发「流量套餐 AI Agent」后端项目。

---

## 一、环境要求

- **Python**：3.9+
- **MySQL**：5.7+ 或 8.0+
- **Redis**：5.0+（可选，用于会话记忆）
- **OpenAI API Key**：Chat 功能需要（可选）

---

## 二、配置环境变量

在 `backend/` 目录下创建 `.env` 文件，或使用项目根目录的 `.env`：

```env
# MySQL 数据库
SQLALCHEMY_DATABASE_URI=mysql+pymysql://用户名:密码@localhost:3306/telecom_package_agent?charset=utf8mb4

# Redis（可选，用于 Agent 会话记忆）
REDIS_URL=redis://localhost:6379/0

# OpenAI API Key（Chat 功能需要）
OPENAI_API_KEY=sk-your-key-here

# OpenAI 兼容服务地址（可选；不填则默认官方 OpenAI）
OPENAI_BASE_URL=https://your-openai-compatible-host/v1
```

示例：

```env
SQLALCHEMY_DATABASE_URI=mysql+pymysql://your_user:your_password@localhost:3306/telecom_package_agent?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://your-openai-compatible-host/v1
```

> 将 `your_user` 和 `your_password` 替换为你的 MySQL 用户名和密码。

---

## 三、数据库初始化

### 3.1 创建数据库并授权

以 MySQL root 用户执行 `scripts/init_db.sql`：

```bash
mysql -u root -p < scripts/init_db.sql
```

或登录 MySQL 后手动执行：

```sql
CREATE DATABASE IF NOT EXISTS telecom_package_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON telecom_package_agent.* TO 'your_user'@'%';
FLUSH PRIVILEGES;
```

### 3.2 执行数据库迁移

在项目根目录（`langchain/telecom-package-agent/`）执行：

```bash
PYTHONPATH=backend backend/.venv/bin/python -m alembic upgrade head
```

首次迁移会创建 `user`、`package`、`benefit`、`user_package`、`user_benefit`、`usage_record`、`complaint` 等表。

---

## 四、安装依赖

### 4.1 创建虚拟环境

```bash
cd backend
python3 -m venv .venv
```

### 4.2 激活虚拟环境并安装依赖

```bash
# macOS / Linux
source .venv/bin/activate

# 安装
pip install -r requirements.txt
```

或直接使用 venv 内的 pip（无需激活）：

```bash
backend/.venv/bin/pip install -r requirements.txt
```

---

## 五、启动后端项目

### 方式一：使用启动脚本（推荐）

```bash
cd backend
chmod +x start.sh
./start.sh
```

### 方式二：使用 uvicorn 命令

```bash
cd backend
export PYTHONPATH=.
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 方式三：从项目根目录启动

```bash
cd langchain/telecom-package-agent
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 六、验证服务

- **健康检查**：`http://localhost:8000/health` 应返回 `{"status":"ok"}`
- **API 文档**：`http://localhost:8000/docs`
- **ReDoc**：`http://localhost:8000/redoc`

---

## 七、项目结构

```
backend/
├── app/
│   ├── api/           # API 路由
│   ├── agent/         # LangChain Agent、工具、函数
│   ├── core/          # 配置
│   ├── models/        # SQLAlchemy 模型
│   ├── schemas/       # Pydantic 模型
│   ├── services/      # 业务逻辑
│   ├── database.py    # 数据库连接
│   └── main.py        # FastAPI 入口
├── .env               # 环境变量（不提交）
├── .venv/             # 虚拟环境
├── requirements.txt
└── start.sh           # 启动脚本
```

---

## 八、常用命令

| 命令 | 说明 |
|------|------|
| `alembic revision --autogenerate -m "描述"` | 生成新迁移（在项目根目录，`PYTHONPATH=backend`） |
| `alembic upgrade head` | 执行迁移 |
| `alembic downgrade -1` | 回滚一次迁移 |

---

## 九、故障排查

### 数据库连接失败

- 确认 MySQL 已启动
- 确认 `.env` 中的 `SQLALCHEMY_DATABASE_URI` 正确
- 确认数据库已创建且用户有权限

### Redis 连接失败

- Chat 功能依赖 Redis 存储会话
- 若未安装 Redis，可先注释相关逻辑或使用内存存储

### 端口被占用

- 修改启动命令中的 `--port`，例如：`--port 8001`
