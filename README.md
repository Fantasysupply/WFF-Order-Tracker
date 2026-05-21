# WFF Order Tracker MVP

WFF Order Tracker 是一个用于履约团队的第一版 MVP 工具，用来从 Wefulfil 订单 API 抓取日常订单，查询外部物流轨迹，识别延误和长时间未更新的异常订单，并生成按客户经理、归属客户拆分的 Excel 清查文档。

> 当前版本已预留 Wefulfil、17TRACK、51Tracking 的正式 API 对接位置。团队准备 API 文档期间，可以使用内置 mock 数据跑通完整流程。

## MVP 能力

- 抓取并标准化 Wefulfil 订单数据。
- 提取订单中的物流跟踪单号。
- 通过 mock、17TRACK 或 51Tracking 适配器查询物流最新轨迹；第一版生产目标默认优先 51track。
- 根据物流模板承诺时效、未更新天数、清关/派送停留时间识别异常订单。
- 生成 Excel `.xlsx` 报告，包含：
  - `异常汇总` sheet；
  - 按客户经理拆分的 sheet；
  - 按归属客户拆分的 sheet。
- 支持 SMTP 发送给履约团队负责人，并支持钉钉群机器人 Markdown 通知与 @ 指定手机号。
- MVP 运行路径只使用 Python 标准库，便于在内部网络受限环境先试跑。

## 项目结构

```text
src/wff_order_tracker/
  analyzer.py          # 异常规则引擎
  cli.py               # 命令行入口
  config.py            # .env 和规则配置加载
  mailer.py            # SMTP 报告发送
  models.py            # 订单、轨迹、异常报告领域模型
  reporting.py         # Excel 生成
  tracking.py          # mock / 17TRACK / 51Tracking 适配器
  wefulfil_client.py   # Wefulfil 订单 API 适配器
config/rules.yaml      # MVP 异常阈值配置
```

## 快速开始

无需安装依赖即可用 mock 数据跑通 MVP：

```bash
cp .env.example .env
PYTHONPATH=src python -m wff_order_tracker.cli --no-email
```

如果暂时没有 API Key，保持 `WEFULFIL_API_KEY` 为空且 `TRACKING_PROVIDER=mock`，工具会使用示例订单和示例轨迹生成 Excel 报告。

如果需要安装为命令行工具，可在网络可访问 Python 包源时执行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
wff-order-tracker --no-email
```

## 配置说明

复制 `.env.example` 为 `.env` 后配置：

| 变量 | 说明 |
| --- | --- |
| `WEFULFIL_BASE_URL` | Wefulfil API Base URL |
| `WEFULFIL_API_KEY` | Wefulfil API Key。为空时使用 demo 订单 |
| `TRACKING_PROVIDER` | `mock`、`17track` 或 `51track`，第一版建议使用 `51track` |
| `TRACKING_API_KEY` | 外部物流查询平台 API Key |
| `REPORT_OUTPUT_DIR` | Excel 输出目录 |
| `DRY_RUN` | `true` 时不实际发送邮件 |
| `MAIL_TO` | 履约团队负责人邮箱，多个邮箱用逗号分隔 |
| `DINGTALK_WEBHOOK` | 钉钉群机器人 webhook |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥 |
| `DINGTALK_AT_MOBILES` | 需要 @ 的履约负责人手机号，多个用逗号分隔 |

## 异常规则

`config/rules.yaml` 目前包含这些阈值：

```yaml
stale_tracking_days: 5
# 距离承诺时效还有几天时开始预警
delay_warning_buffer_days: 2
customs_stale_days: 3
delivery_stale_days: 2
waiting_pickup_stale_days: 2
super_delay_days_after_promise: 7
```

规则引擎会识别：

- 已超承诺时效未签收；
- 临近承诺时效风险；
- 物流超过阈值未更新；
- 清关节点停留过久；
- 派送节点停留过久；
- 超长延误；
- 派送失败；
- 退件/退回风险；
- 等待取件超时；
- 物流平台标记异常；
- 缺少物流单号。

## 钉钉与知识库说明

- 钉钉群机器人只能在群内发消息并 @ 手机号；如果需要精准私聊，需要后续接入钉钉企业内部应用。详细配置见 `docs/dingtalk_setup.md`。
- 报告分析需要知识库。第一版已提供 `knowledge_base/exception_rules.md` 和 `config/exception_knowledge.yaml`，用于沉淀 51track 状态码、异常类型、风险等级和处理动作。
- 每天 9 点运行、51track、钉钉和 Wefulfil API 配置清单见 `docs/next_steps.md`。

## 等待 API 文档后需要补充的映射

拿到 Wefulfil API 文档后，优先补充：

1. `src/wff_order_tracker/wefulfil_client.py` 中的订单字段映射。
2. Wefulfil 分页字段、筛选日常订单的时间参数、订单状态过滤规则。
3. `src/wff_order_tracker/tracking.py` 中 17TRACK / 51Tracking 的正式响应字段映射。
4. 按真实物流模板确认 `promised_delivery_days` 来源和覆盖规则。
5. SMTP 或企业微信/飞书/钉钉通知方式。

## 测试

```bash
PYTHONPATH=src pytest
```
