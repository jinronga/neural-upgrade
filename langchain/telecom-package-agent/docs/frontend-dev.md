# 前端开发文档

本文档说明如何配置、启动和开发「流量套餐 AI Agent」前端项目。

---

## 一、技术栈

- **React 18**
- **TypeScript**
- **Vite 5**
- **Tailwind CSS**
- **Ant Design 5**
- **Axios**
- **React Router v6**

---

## 二、环境要求

- **Node.js**：18+（推荐 LTS）
- **Yarn**：1.22+（或 Yarn Berry）

可通过以下命令检查版本：

```bash
node -v
yarn -v
```

---

## 三、安装依赖

在项目根目录执行：

```bash
cd frontend
yarn install
```

---

## 四、环境变量

前端使用 `VITE_API_BASE_URL` 作为后端地址。

- 未配置时默认使用：`http://localhost:8000`
- 建议在 `frontend/.env` 或 `frontend/.env.local` 配置：

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 五、启动与构建

### 5.1 开发模式

```bash
cd frontend
yarn dev
```

默认访问地址：`http://localhost:5173`

### 5.2 生产构建

```bash
cd frontend
yarn build
```

### 5.3 本地预览构建产物

```bash
cd frontend
yarn preview
```

### 5.4 TypeScript 类型检查

```bash
cd frontend
yarn tsc --noEmit
```

---

## 六、项目结构

```
frontend/
├── src/
│   ├── components/           # 全局组件（如布局）
│   ├── contexts/             # 全局上下文（当前用户 ID）
│   ├── hooks/                # 通用 Hooks
│   ├── pages/
│   │   ├── Chat/             # 智能对话页
│   │   ├── Dashboard/        # 业务看板
│   │   ├── Packages/         # 套餐列表/筛选/推荐/对比
│   │   └── Benefits/         # 权益中心（待领/已领）
│   ├── services/
│   │   └── api.ts            # API 请求封装与类型
│   ├── types/                # 通用类型
│   ├── utils/                # 工具函数
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 七、页面与交互说明

### 7.1 全局布局（Layout）

- 顶部导航：`/chat`、`/dashboard`、`/packages`、`/benefits`
- 右上角支持切换 `用户ID`，并持久化到 `localStorage`
- 所有页面请求均使用当前用户 ID

### 7.2 Chat（对话）

- 支持消息发送、建议问题点击、转人工
- 对接接口：
  - `POST /api/v1/chat`
  - `POST /api/v1/chat/transfer-human`
- 若后端 Chat 返回 500，会提示检查后端 LLM 鉴权配置

### 7.3 Dashboard（仪表盘）

- 聚合展示：
  - 用户信息
  - 当前套餐
  - 当前流量用量
  - 历史用量趋势
  - 待领/已领权益统计
- 对接接口：
  - `GET /api/v1/users/{user_id}`
  - `GET /api/v1/users/{user_id}/packages`
  - `GET /api/v1/usage/current/{user_id}`
  - `GET /api/v1/usage/history/{user_id}`
  - `GET /api/v1/benefits/pending/{user_id}`
  - `GET /api/v1/users/{user_id}/benefits`

### 7.4 Packages（套餐列表）

- 支持关键词、人群、价格筛选
- 支持最多 3 个套餐对比
- 支持“智能推荐”参数输入（预算、最小流量、返回条数）
- 对接接口：
  - `GET /api/v1/packages`
  - `POST /api/v1/packages/recommend`

### 7.5 Benefits（权益中心）

- 待领取权益列表
- 已领取权益列表
- 领取后自动刷新状态
- 对接接口：
  - `GET /api/v1/benefits/pending/{user_id}`
  - `GET /api/v1/users/{user_id}/benefits`
  - `POST /api/v1/benefits/claim`

---

## 八、API 开发规范

API 统一在 `src/services/api.ts` 中维护：

- 使用 axios 实例统一 `baseURL`、超时、拦截器
- 优先使用后端原始字段命名（snake_case）
- 页面层做最小必要映射，避免重复封装
- 错误提示优先显示后端 `detail` 字段

---

## 九、联调建议流程

1. 启动后端（默认 `http://localhost:8000`）
2. 启动前端（`yarn dev`）
3. 打开页面后先确认右上角 `用户ID`（默认建议 `1`）
4. 按页面联调：
   - Dashboard：检查聚合数据是否展示
   - Packages：检查列表、筛选、推荐
   - Benefits：检查领取流程和库存变化
   - Chat：检查消息收发与转人工

---

## 十、常见问题

### 10.1 页面报 `User not found`

- 当前用户 ID 在数据库不存在
- 处理：切换为有效用户 ID（如 `1`），或补充测试数据

### 10.2 Chat 接口返回 500

- 常见原因：`OPENAI_API_KEY` / `OPENAI_BASE_URL` 配置错误
- 处理：检查后端 `.env` 并重启后端服务

### 10.3 跨域或请求失败

- 确认 `VITE_API_BASE_URL` 与后端地址一致
- 确认后端已启动，且端口可访问

### 10.4 构建体积 warning（chunk > 500kb）

- 当前为警告，不影响运行
- 如需优化，可做路由懒加载和手动分包

---

## 十一、前端开发验收清单

- [ ] `yarn dev` 可正常启动
- [ ] `yarn tsc --noEmit` 通过
- [ ] `yarn build` 通过
- [ ] 四个页面（Chat/Dashboard/Packages/Benefits）均可访问
- [ ] 用户 ID 切换后接口请求生效
- [ ] 套餐推荐与权益领取链路可用
- [ ] Chat 返回异常时有可读错误提示
