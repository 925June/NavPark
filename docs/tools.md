# NavPark Tool 层

版本：1.0  
工具框架：LangChain Core Tools  
注册表：`app/tools/registry.py`  
权限绑定：`app/tools/access.py`

## 1. 设计目标

Tool 负责执行边界清楚的确定性能力，Agent 负责理解问题、选择流程和组织语言。
本层遵循以下原则：

1. 参数必须有 Pydantic 校验。
2. 返回值使用统一成功或失败结构。
3. 只读工具可以直接接入确定性 Agent。
4. 有副作用的工具必须获得真实业务结果、幂等键和操作审计后才能启用。
5. 每个 Agent 只能获得明确绑定的工具。
6. 风险策略、Guardrail、鉴权和持久化不能做成模型自由调用的业务 Tool。

## 2. 工具目录

| Tool | 权限 | 当前接入 | 允许使用 |
| --- | --- | --- | --- |
| `get_parking_availability` | 只读 | 是 | ParkingAgent |
| `plan_parking_route` | 只读 | 是 | ParkingAgent |
| `search_parking_knowledge` | 只读 | 是 | Reservation/Pricing/Support |
| `calculate_parking_fee` | 计算 | 已实现、未自动调用 | PricingAgent |
| `validate_reservation_request` | 校验 | 已实现、未自动调用 | ReservationAgent |

访问目录：

```http
GET /tools
```

该接口同时返回工具职责、可调用 Agent 和运行时绑定。

## 3. 返回契约

成功：

```json
{
  "ok": true,
  "data": {},
  "source": "parking_service",
  "as_of": "2026-10-25T12:00:00+00:00",
  "error": null,
  "error_code": null,
  "metadata": {}
}
```

失败：

```json
{
  "ok": false,
  "data": null,
  "source": "parking_navigation_service",
  "as_of": "2026-10-25T12:00:00+00:00",
  "error": "车位不存在、不可用或不是标准车位",
  "error_code": "parking_route_unavailable",
  "metadata": {}
}
```

Agent 必须检查 `ok`，不能把失败结果当成业务成功。

## 4. 最小权限

```text
SupervisorAgent         无工具
ParkingAgent            get_parking_availability
                        plan_parking_route
ReservationAgent        search_parking_knowledge
                        validate_reservation_request
PricingAgent            search_parking_knowledge
                        calculate_parking_fee
SupportAgent            search_parking_knowledge
JudgeAgent              无业务工具
ResponseAgent           无业务工具
```

`JudgeAgent` 不获授业务工具，避免审核模型在判断过程中改变数据或执行操作。
`ResponseAgent` 不获授工具，避免最终输出节点调用新的外部业务系统。

## 5. 当前接线的三条只读链路

### 停车与路线

```text
ParkingAgent
  → get_parking_availability
  → parking_service.get_availability
  → plan_parking_route
  → parking_service.get_route
  → A*
```

ParkingAgent 是唯一的停车业务 Agent。车位 Tool 和路线 Tool
仍然各自保持独立、可测试的边界。

### 知识检索

```text
ReservationAgent / PricingAgent / SupportAgent
  → search_parking_knowledge
  → RAG Retriever
```

三个知识型 Agent 使用同一个检索 Tool，但分别保留自己的业务提示词。

## 6. 暂不自动接线的原因

`calculate_parking_fee` 只能根据调用方明确提供的费率和时长计算，
不能自行补齐未检索到的正式价格。

`validate_reservation_request` 只验证时间和车牌参数，
返回结果明确包含 `reservation_created: false`。它不会创建预约。

当前没有以下真实 Tool：

- `create_reservation`
- `cancel_reservation`
- `get_reservation_status`
- `create_payment_order`
- `request_refund`
- `open_gate`
- `create_human_escalation`

在接入这些能力前，系统不能声称已完成真实预约、退款、支付、开闸或人工转接。

## 7. 新增 Tool 的步骤

1. 在 `app/tools/` 对应模块中定义 Pydantic 输入模型。
2. 使用 `@tool` 声明工具名、描述和参数模型。
3. 返回 `tool_success()` 或 `tool_failure()`。
4. 在 `app/tools/registry.py` 注册权限和职责。
5. 在 `app/tools/access.py` 只授权给需要的 Agent。
6. 在对应 Agent 中显式注入 Tool，避免全局开放。
7. 增加成功、参数错误、业务失败和权限测试。

有副作用的工具还必须增加：

- 用户身份由服务端注入，不能信任模型提供的 `user_id`。
- 幂等键。
- 二次确认。
- 超时和重试策略。
- 审计日志。
- 真实后端成功结果。
- 回滚或补偿方案。

## 8. 与 LangGraph 的关系

当前三个只读 Tool 由确定性 Agent 节点直接调用，流程可预测。
只有未来需要让模型在多个只读工具之间动态选择时，才建议增加 LangGraph
`ToolNode`，并继续使用上述最小权限绑定。
