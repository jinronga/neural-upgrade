## 项目联调与验收 Checklist

本清单用于在本地或测试环境对「流量套餐 AI Agent」项目进行联调与验收，建议按顺序逐项完成并打勾。

---

### 一、环境与基础配置

- [ ] **环境变量**：在项目根目录配置 `.env` 或等效配置，至少包含：
  - [ ] `SQLALCHEMY_DATABASE_URI`
  - [ ] `OPENAI_API_KEY`
  - [ ] `REDIS_URL`
- [ ] **前端 API 地址**：在 `frontend` 配置 `VITE_API_BASE_URL` 指向后端，例如 `http://localhost:8000`。
- [ ] **依赖安装**：
  - [ ] 后端（virtualenv 或 poetry/pip）：安装 FastAPI / SQLAlchemy / LangChain / Redis 驱动 等依赖。
  - [ ] 前端（在 `frontend`）：`yarn install` 或等效命令执行成功。

---

### 二、数据库与迁移

- [ ] **数据库**：MySQL 中已创建目标数据库（如 `telecom_package_agent`），账号权限正确。
  - 首次需执行 `scripts/init_db.sql` 中的 SQL（以 root 登录 MySQL）：
    ```sql
    CREATE DATABASE IF NOT EXISTS telecom_package_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON telecom_package_agent.* TO 'your_user'@'%';
    FLUSH PRIVILEGES;
    ```
- [ ] **Alembic 初始化**（首轮）：
  - [ ] `alembic revision --autogenerate -m "init"` 生成初始迁移（如已存在可跳过）。
  - [ ] `alembic upgrade head` 执行迁移成功，无报错。
- [ ] **核心表检查**：确认以下表已经创建：
  - [ ] `user` / `package` / `benefit`
  - [ ] `user_package` / `user_benefit` / `usage_record`
  - [ ] `complaint` 等

---

### 三、后端服务启动与基础检查

- [ ] 启动后端服务：
  - [ ] 在 `backend` 目录运行：`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] 健康检查：
  - [ ] 访问 `GET /health` 返回 `{"status": "ok"}`。
- [ ] 文档与路由：
  - [ ] 打开 `http://localhost:8000/docs` 能看到 `/api/v1/*` 路由列表且无异常。

---

### 四、核心 REST 接口联调

#### 4.1 用户与套餐

- [ ] `GET /api/v1/users/{user_id}` 返回用户基础信息。
- [ ] `GET /api/v1/users/{user_id}/packages` 返回当前用户套餐列表。

#### 4.2 套餐与推荐

- [ ] `GET /api/v1/packages` 返回可用套餐列表。
- [ ] `POST /api/v1/packages/recommend` 使用示例参数（预算、流量需求）返回推荐结果。

#### 4.3 权益

- [ ] `GET /api/v1/benefits/pending/{user_id}` 能列出待领权益。
- [ ] `POST /api/v1/benefits/claim` 能成功领取一条权益（数据库状态有变更）。

#### 4.4 用量

- [ ] `GET /api/v1/usage/current/{user_id}` 返回当前总用量（MB）。
- [ ] `GET /api/v1/usage/history/{user_id}` 返回最近一段时间的用量记录。

#### 4.5 聊天与 Agent

- [ ] `POST /api/v1/chat`：
  - [ ] 使用简单文本（如“我现在什么套餐？”）能获得合理回复。
  - [ ] 多轮对话中 Agent 能记住上下文（例如再次询问“那帮我推荐一个套餐？”）。
- [ ] `POST /api/v1/chat/transfer-human` 创建人工转接请求不报错。
- [ ] `GET /api/v1/chat/history/{session_id}` 能返回该会话的历史消息。

---

### 五、Agent 能力验证（对话体验）

建议通过 `/chat` 页面或直接调用 `/api/v1/chat`，测试以下能力：

- [ ] **套餐查询**：如“我现在用的什么套餐？”、“有哪些学生套餐？”。
- [ ] **套餐推荐**：如“帮我按我最近的用量推荐一个套餐”。
- [ ] **用量查询与预警**：如“我这个月用了多少流量？”、“会不会不够用？”、“要不要加油包？”。
- [ ] **权益管理**：如“我有哪些权益没领？”、“帮我领一下腾讯视频会员”。
- [ ] **套餐变更**：如“我要把29档换到49档”、“确认升级套餐”。
- [ ] **投诉处理**：如“网速很慢”、“我被多扣了话费”，验证自动诊断与工单创建。
- [ ] **续费与到期提醒**：如“套餐什么时候到期？”、“有没有续费优惠？”。

---

### 六、前端页面联调

#### 6.1 启动前端

- [ ] 在 `frontend` 目录执行：
  - [ ] `yarn install`
  - [ ] `yarn dev`
- [ ] 浏览器访问 Vite 提供的地址（默认 `http://localhost:5173`）正常。

#### 6.2 页面功能

- [ ] `Chat` 页面：
  - [ ] 能正常发送和接收消息。
  - [ ] 建议问题 chips 可点击快速发送。
  - [ ] 在提示需要时出现“转人工”入口。
- [ ] `Dashboard` 页面：
  - [ ] 用量环形图、趋势图有数据（哪怕是示例）。
  - [ ] 当前套餐区域显示与后端一致。
  - [ ] 快捷操作按钮（查流量、领权益、充话费、找客服）跳转正确。
- [ ] `Packages` 页面：
  - [ ] 能加载套餐列表并分页/网格展示。
  - [ ] 筛选栏（关键词、人群、价格）生效。
  - [ ] 详情弹窗与套餐对比区域工作正常。
- [ ] `Benefits` 页面：
  - [ ] 待领/已领权益列表展示正确。
  - [ ] 领取动作能调用后端并更新页面状态。

---

### 七、配置分环境与部署前检查

- [ ] 根据环境（开发 / 测试 / 生产）拆分配置或使用环境变量：
  - [ ] 不在代码库中硬编码敏感信息（API Key、数据库密码等）。
- [ ] 日志与错误处理：
  - [ ] 后端异常时返回清晰的错误信息，而非裸露堆栈。
  - [ ] 前端 axios 拦截器能统一提示网络 / 权限类错误。
- [ ] “冒烟测试”完整业务链：
  - [ ] 新建测试用户与套餐/权益数据。
  - [ ] 依次体验：Dashboard → Chat 查询套餐/用量 → Packages 浏览/对比 → Benefits 领取 → 投诉一个场景 → 查看续费提醒。
