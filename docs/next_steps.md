# 下一步实施清单

## 已确认方向

1. 第一版物流轨迹平台优先对接 `51track`。
2. 异常通知优先使用钉钉。
3. 超过 5 天无物流更新归类为异常。
4. 需要额外识别超长延误、派送失败、退件/退回、等待取件等异常。
5. 每天上午 9 点运行报告。
6. 报告需要让负责人按 AM 客户经理、客户、异常类型查看订单和处理建议。

## 你需要提供给开发工具的配置

### 51track

- `TRACKING_API_KEY`
- API 文档链接
- 批量查询接口示例
- 是否需要先注册 tracking number
- 4 类脱敏响应样例：正常运输、已签收、派送失败/退件、等待取件
- 状态枚举说明
- 限流规则

### 钉钉

- `DINGTALK_WEBHOOK`
- `DINGTALK_SECRET`
- 履约负责人手机号，填入 `DINGTALK_AT_MOBILES`
- 钉钉机器人所在群名

> 说明：钉钉群机器人只能向群发送消息并 @ 指定手机号。若要真正一对一私聊指定负责人，需要企业内部应用机器人，并提供 AppKey、AppSecret、用户 userId 或手机号到 userId 的映射接口。

### Wefulfil 订单 API

- `WEFULFIL_BASE_URL`
- `WEFULFIL_API_KEY`
- 鉴权方式和 Header 示例
- 订单列表接口
- 分页规则
- 发货时间/更新时间筛选参数
- 订单状态枚举和排除状态
- 订单 JSON 样例，至少包含正常已发货、一单多包裹、缺少物流单号三类
- 客户字段、客户经理字段、物流模板字段、承诺时效字段

## 9 点定时运行建议

Linux cron 示例：

```cron
0 9 * * * cd /workspace/WFF-Order-Tracker && PYTHONPATH=src python -m wff_order_tracker.cli >> reports/daily_run.log 2>&1
```

上线前请保持 `DRY_RUN=true` 测试；确认钉钉群、@ 手机号、51track API 都正确后再改成 `DRY_RUN=false`。
