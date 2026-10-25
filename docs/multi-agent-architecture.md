# NavPark 多智能体架构 v2.1

工作流引擎：LangGraph  
Web 宿主：FastAPI  
Agent 数量：7  
Tool 数量：5

## 1. 设计原则

多 Agent 不是节点越多越好。只有需要独立理解、判断或生成内容的角色才拆成 Agent；
查询、检索、计算、路线规划和内容检查属于 Tool 或确定性步骤。

本项目坚持三点：

1. 业务专家负责回答问题。
2. Tool 负责边界清楚的数据和计算。
3. 所有业务草稿统一经过审核和最终答复节点。

## 2. 工作流

```text
                    ┌──────────────────┐
用户请求 ──────────→│ SupervisorAgent  │
                    └────────┬─────────┘
                             │
       ┌─────────────┬───────┴───────┬─────────────┐
       ▼             ▼               ▼             ▼
  ParkingAgent  ReservationAgent  PricingAgent  SupportAgent
       │             │               │             │
       │             └───────┬───────┘             │
       └─────────────────────┼─────────────────────┘
                             ▼
                     ┌──────────────────┐
                     │ JudgeAgent       │
                     │ 风险审核与待核实  │
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ ResponseAgent    │
                     │ 合成 + Guardrail  │
                     │ 持久化            │
                     └────────┬─────────┘
                              ▼
                          最终答复
```

## 3. 七个 Agent

| Agent | 职责 | 不做的事 |
| --- | --- | --- |
| SupervisorAgent | 判断问题属于停车、预约、价格或售后 | 不查询业务数据，不生成草稿 |
| ParkingAgent | 调用车位和路线 Tool，生成确定性停车与导航答复 | 不让模型修改车位号或路线 |
| ReservationAgent | 检索资料并解释预约、修改和取消规则 | 不创建真实预约 |
| PricingAgent | 检索资料并解释价格和计费规则 | 不执行支付或退款 |
| SupportAgent | 回答设施、营业时间、服务和一般售后问题 | 不编造政策或人工处理结果 |
| JudgeAgent | 执行风险策略和结构化模型审核 | 不改写答复，不保存会话 |
| ResponseAgent | 合成最终答复、追加人工提示、执行 Guardrail 并保存 | 不查询业务数据，不重新判断意图 |

Agent 目录通过 `GET /agents` 查看。

## 4. Tool 分工

| Tool | 使用者 | 性质 |
| --- | --- | --- |
| `get_parking_availability` | ParkingAgent | 只读 |
| `plan_parking_route` | ParkingAgent | 只读、A* |
| `search_parking_knowledge` | Reservation/Pricing/Support | 只读 RAG |
| `calculate_parking_fee` | PricingAgent | 纯计算，未自动接线 |
| `validate_reservation_request` | ReservationAgent | 参数校验，未自动接线 |

Tool 的统一返回结构、权限绑定和扩展规则见 `docs/tools.md`。

## 5. 两条业务路径

### 停车

```text
SupervisorAgent
  → ParkingAgent
      → get_parking_availability
      → plan_parking_route
      → 确定性答复草稿
  → JudgeAgent（结构化数据直接通过）
  → ResponseAgent
```

停车路径不调用 DeepSeek。车位、距离、楼层、坡道和路线都由 Tool 提供。

### 预约、价格或售后

```text
SupervisorAgent
  → ReservationAgent / PricingAgent / SupportAgent
      → search_parking_knowledge
      → DeepSeek 生成业务草稿
  → JudgeAgent
  → ResponseAgent
```

知识 Agent 共用同一个检索 Tool，但每个 Agent 保留自己的业务提示词和职责。

## 6. 审核和人工待核实

JudgeAgent 先执行确定性风险策略，再由 DeepSeek 输出结构化审核结果。
以下情况会设置 `requires_human = true`：

- 用户明确要求人工、投诉、退款、支付争议或法律责任。
- 涉及事故、车辆损坏、火灾、医疗、失物或敏感信息。
- 答复声称已经预约、支付、退款、锁车位或开闸。
- 回答包含没有证据支持的关键事实。
- 审核输出无法解析。

ResponseAgent 在最终答复中追加：

> 该问题需要人工进一步核实。当前系统尚未完成真实人工审核，请联系现场服务台。

这里没有单独的 HumanAgent，因为当前系统没有真实人工工单系统。
增加一个只负责拼接提示的 Agent 不会带来独立智能能力。

## 7. 状态与公开接口

主要状态分组：

- 请求：`question`, `user_id`, `session_id`, `history`, `location`
- 路由：`next_agent`, `intent`, `workflow_plan`
- 证据：`retrieved_context`, `context_sources`
- Tool：`api_result`, `tool_results`
- 草稿与审核：`draft_response`, `audit_result`, `requires_human`
- 最终输出：`response`, `human_review_status`, `guardrail_failures`
- 执行摘要：`agent_trace`

`/chat` 只返回用户需要的答复、审核摘要、Tool 摘要和执行轨迹，
不返回提示词或知识库正文。

## 8. 失败策略

| 失败点 | 行为 |
| --- | --- |
| 知识 Tool 失败 | 不中断请求，按无资料模式回答 |
| 车位或路线 Tool 失败 | 请求返回服务错误，不编造路线 |
| 审核模型失败 | 当前请求失败，不放行未审核答复 |
| 审核输出不可解析 | 标记待人工核实并继续生成保守答复 |
| Guardrail 失败 | 使用中文安全兜底 |
| DeepSeek 未配置 | 停车路径仍可运行，其他问题返回 503 |

## 9. 扩展规则

新增 Agent 前先回答：

- 它是否需要独立判断或领域提示词？
- 它是否只是查询、计算或格式转换？
- 它能否作为现有 Agent 的 Tool？

只有第一个问题为“是”、后两个问题为“否”时，才新增 Agent。

新增 Tool 时：

1. 定义 Pydantic 参数模型。
2. 使用 LangChain `@tool`。
3. 返回 `tool_success` 或 `tool_failure`。
4. 在 `app/tools/registry.py` 注册。
5. 在 `app/tools/access.py` 授权给最少的 Agent。
6. 增加成功、失败、越权和回归测试。

预约、支付、退款、开闸和人工工单等写操作必须连接真实系统，
并具有服务端身份注入、幂等、确认和审计后才能上线。
