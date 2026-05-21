# 钉钉通知配置说明

## 群机器人方式（当前 MVP 支持）

1. 在履约负责人所在钉钉群添加自定义机器人。
2. 安全设置建议选择“加签”，得到 `DINGTALK_SECRET`。
3. 复制 webhook 到 `DINGTALK_WEBHOOK`。
4. 把履约负责人手机号填到 `DINGTALK_AT_MOBILES`，多个手机号用英文逗号分隔。
5. 测试时保持 `DRY_RUN=true`，确认输出内容后再设置 `DRY_RUN=false`。

```env
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=SECxxx
DINGTALK_AT_MOBILES=13800000000,13900000000
```

## 精准私聊方式（后续增强）

钉钉群机器人不能直接私聊某个人，只能在群内 @ 手机号。若业务要求“精准发送到指定人的钉钉私聊”，需要企业内部应用机器人，并提供：

- AppKey / Client ID
- AppSecret / Client Secret
- 企业 CorpId
- 用户手机号到 userId 的映射
- 发送工作通知或单聊消息的权限

拿到这些信息后，可以新增企业应用通知通道。
