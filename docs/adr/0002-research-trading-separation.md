# ADR-0002：分离研究面与交易面

- 状态：Accepted
- 日期：2026-08-03
- 决策负责人：LXL-QuantAxis Architecture
- 适用范围：研究、回测、风险、模拟交易和 AI Agent

## 背景

研究工作允许探索、参数调整和失败；交易工作要求确定性、幂等、权限、审计和可恢复。当前 UI、AI、回测和模拟交易可以共享或直接修改底层状态，风险检查也没有在订单前形成强制门。若继续共用同一自由调用路径，研究便利性会侵蚀交易正确性。

## 决策

V2.0 逻辑上分为三个平面：

### Research Plane

- 读取授权数据快照。
- 构造因子、策略草案和研究实验。
- 运行回测、Walk-Forward 和稳健性测试。
- 不能修改交易账户、现金账本或直接提交订单。

### Trading Plane

- 只接受已版本化、已审批且满足数据要求的策略信号。
- 固定执行 `Signal -> OrderIntent -> PreTradeRisk -> ApprovedOrder/RejectedOrder -> Execution -> Fill -> Ledger`。
- 现金和持仓只能由 Fill 与公司行动驱动。
- 回测与 Paper 共用订单、风险和账本契约，只替换 Clock、DataFeed 和 Broker Adapter。

### Control Plane

- 管理身份、组织、权限、配置、任务、版本、审计、监控和 Kill Switch。
- 不直接修改领域账本。

## AI 权限

- AI Agent 只能读取授权研究数据并创建 Research Note、Strategy Draft 或 Research Run。
- AI 不能批准风险例外、修改账本或持有 Broker Credential。
- Strategy Draft 必须人工确认；进入 Paper 前必须通过 Promotion Gate。

## 结果

### 正面影响

- 研究探索不会直接影响账户状态。
- 风控和审计成为不可绕过的系统能力。
- Paper Trading 可作为未来 Broker Adapter 的契约验证场。
- AI 的权限边界清晰，可独立评估和降级。

### 代价

- 需要定义事件、状态机、身份和审批模型。
- 部分现有 UI 快捷调用必须改经 Application Service。
- 研究到 Paper 多一道确认和验证流程。

## 验收原则

- 未经风险审批的订单数必须为 0。
- Research Plane 测试证明无法调用交易写接口。
- 每个订单可追溯到策略版本、信号、风险决定和 Actor。
- AI 输出数据过期或 Schema 失败时只能降级，不能继续提交交易意图。

## 备选方案

- 通过编码约定区分研究和交易：拒绝。约定不能替代权限和契约。
- 为 AI 提供受限 Broker 凭据：拒绝。风险收益不匹配。
- 回测、Paper、Live 使用完全不同模型：拒绝。会造成语义漂移。
