# Telecom Agent 场景统计与案例清单

## 1. 统计范围

本清单基于以下代码实现统计：

- `backend/app/agent/agent.py`
- `backend/app/agent/functions/*.py`
- `backend/app/agent/tools/*.py`

统计口径：

- 场景域：`domain` 路由层可识别的业务大类
- 意图：`intent.type` 的细分能力
- 案例：可直接用于联调/测试的用户话术样例

## 2. 场景统计总览

### 2.1 Domain（业务域）统计

| 类型 | 数量 | 说明 |
| --- | ---: | --- |
| 已定义业务域 | 6 | `package` / `usage` / `benefit` / `change` / `complaint` / `reminder` |
| 兜底域 | 1 | `other`（走通用 LLM 回复） |
| 合计 | 7 | 含兜底 |

### 2.2 Intent（细分意图）统计

| 域 | 显式意图数 | 当前状态 |
| --- | ---: | --- |
| package | 5 | 3 个已实装，2 个预留 |
| usage | 4 | 全部已实装 |
| benefit | 4 | 全部已实装 |
| change | 3 | 全部已实装（历史当前为空列表占位） |
| complaint | 1+ | 由投诉分类结果再细分处理 |
| reminder | 2 | 全部已实装 |
| 合计 | 19 | 含 package 预留意图 |

### 2.3 Tool（LangChain 工具）统计

| 类别 | 数量 | 说明 |
| --- | ---: | --- |
| 已在 Agent 挂载工具 | 6 | `QueryUsageTool` / `RecommendPackageTool` / `GetPendingBenefitsTool` / `ClaimBenefitTool` / `HandleComplaintTool` / `CheckNetworkStatusTool` |
| 已实现但未挂载工具 | 2 | `BillingQueryTool` / `ProcessRefundTool` |
| 工具总数 | 8 | `backend/app/agent/tools` 下定义 |

## 3. 路由矩阵（Domain -> Intent -> 能力）

### 3.1 package 域

| intent.type | 能力 | 实现状态 |
| --- | --- | --- |
| `query_current` | 查询当前生效套餐 | 已实现 |
| `query_available` | 查询可选套餐列表 | 已实现 |
| `need_recommend` | 根据用量推荐套餐 | 已实现 |
| `query_detail` | 查询某套餐详情 | 预留（已识别，主路由未专门处理） |
| `compare` | 套餐对比 | 预留（已识别，主路由未专门处理） |

### 3.2 usage 域

| intent.type | 能力 | 实现状态 |
| --- | --- | --- |
| `query_usage` | 查询当前用量 | 已实现 |
| `query_remain` | 查询剩余流量 | 已实现 |
| `usage_warning` | 用量超阈值预警 | 已实现 |
| `buy_topup` | 推荐流量加油包 | 已实现 |

### 3.3 benefit 域

| intent.type | 能力 | 实现状态 |
| --- | --- | --- |
| `query_pending` | 查询待领权益 | 已实现 |
| `claim` | 领取单个权益 | 已实现 |
| `claim_all` | 一键领取全部权益 | 已实现 |
| `expired_complaint` | 过期权益补偿判断 | 已实现 |

### 3.4 change 域

| intent.type | 能力 | 实现状态 |
| --- | --- | --- |
| `want_change` | 套餐变更资格与费用说明 | 已实现 |
| `confirm_change` | 提交变更申请 | 已实现 |
| `change_history` | 查询变更历史 | 占位实现（当前返回空） |

### 3.5 complaint 域

投诉先经分类，再按类型处理：

| complaint.type | 能力 | 实现状态 |
| --- | --- | --- |
| `network_slow` | 网络诊断 + 自动补偿 | 已实现 |
| `overcharge` | 扣费争议核查 + 退款/工单 | 已实现 |
| `benefit_missing` | 权益投诉转权益处理 | 已实现 |
| 其他 | 创建投诉工单 | 已实现 |

### 3.6 reminder 域

| intent.type | 能力 | 实现状态 |
| --- | --- | --- |
| `check_expiry` | 套餐到期检查 + 续费提醒 | 已实现 |
| `renewal_offer` | 续费优惠查询 | 已实现 |

### 3.7 other 兜底域

| 路由 | 能力 | 实现状态 |
| --- | --- | --- |
| `other` | 走通用 LLM（带系统提示和会话记忆） | 已实现 |

## 4. 案例清单（可直接用于测试）

> 说明：以下案例按“用户话术 -> 预期路由 -> 预期能力”设计，适合接口联调、回归测试和 UAT。

| 案例ID | 用户话术示例 | 预期路由 | 预期结果要点 |
| --- | --- | --- | --- |
| PKG-01 | 我现在用的是什么套餐？ | package / query_current | 返回当前套餐名、月费、流量等 |
| PKG-02 | 给我看看现在有哪些在售套餐 | package / query_available | 返回套餐列表（最多前几条） |
| PKG-03 | 我每月预算 80，推荐一个套餐 | package / need_recommend | 给出推荐套餐和推荐理由 |
| PKG-04 | 帮我看下 39 元套餐详情 | package / query_detail | 当前应落兜底回复（预留能力） |
| PKG-05 | 帮我对比下 39 和 59 套餐 | package / compare | 当前应落兜底回复（预留能力） |
| USG-01 | 我这个月用了多少流量？ | usage / query_usage | 返回已用流量、剩余流量等 |
| USG-02 | 还剩多少流量，够不够月底？ | usage / query_remain | 返回剩余量和简要建议 |
| USG-03 | 会不会超出套餐？ | usage / usage_warning | 返回阈值预警或“当前正常” |
| USG-04 | 给我推荐一个 5G 加油包 | usage / buy_topup | 返回推荐加油包及价格 |
| BEN-01 | 我还有什么权益没领？ | benefit / query_pending | 返回待领权益列表和紧急权益 |
| BEN-02 | 帮我领腾讯视频会员 | benefit / claim | 返回领取成功/失败与交付信息 |
| BEN-03 | 一键帮我全部领取 | benefit / claim_all | 返回成功数与失败数 |
| BEN-04 | 我的咖啡券过期了怎么办 | benefit / expired_complaint | 返回补偿判定（免费/积分/不可补） |
| CHG-01 | 我要从当前套餐升级到 59 套餐 | change / want_change | 返回可否变更、费用、生效时间 |
| CHG-02 | 确认办理这个变更 | change / confirm_change | 返回提交结果、是否需支付差价 |
| CHG-03 | 查下我最近的改套餐记录 | change / change_history | 当前返回“暂无记录” |
| CMP-01 | 网络特别卡，视频一直转圈 | complaint / network_slow | 诊断网络并给补偿或优化建议 |
| CMP-02 | 你们重复扣费了，给我退钱 | complaint / overcharge | 自动核查并退款或建工单 |
| CMP-03 | 我的权益没到账，太离谱了 | complaint / benefit_missing | 转权益投诉处理逻辑 |
| CMP-04 | 我要投诉你们服务态度 | complaint / other | 创建投诉工单并回传工单号 |
| REM-01 | 套餐什么时候到期？ | reminder / check_expiry | 返回到期时间、是否临近到期 |
| REM-02 | 我有续费优惠吗？ | reminder / renewal_offer | 返回是否有优惠及节省金额 |
| OTH-01 | 你是谁？你会做什么？ | other | 走通用对话，返回助手能力说明 |

## 5. 当前可见的能力边界

### 5.1 已识别但未专门实现

- `package.query_detail`
- `package.compare`

这两类意图在识别层已定义，但当前主路由没有独立分支处理，会走通用 LLM 兜底。

### 5.2 工具层实现但未挂载

- `BillingQueryTool`
- `ProcessRefundTool`

工具代码已存在，但当前 `TelecomAgent._init_tools()` 未注入这两个工具。

## 6. 建议的下一步（可选）

1. 补齐 `query_detail` / `compare` 两个 package 专用 handler，并接入 `get_package_detail` / `compare_packages`。
2. 将 `BillingQueryTool` / `ProcessRefundTool` 挂载到 Agent 工具列表，形成完整“账单与退款”场景闭环。
3. 基于本清单生成自动化回归脚本（按案例 ID 驱动），持续验证路由与回复稳定性。
