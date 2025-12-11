# 配置私有数据说明

## ⚠️ 重要：请勿提交敏感信息到GitHub

本文件说明如何配置您的私有数据。

### 1. 创建 .env 文件

复制 `.env.example` 为 `.env`:

```bash
cp .env.example .env
```

### 2. 填写您的Telegram信息

编辑 `.env` 文件:

```env
# Telegram Bot配置
TELEGRAM_BOT_TOKEN=你的Bot Token
TELEGRAM_CHAT_ID=你的Chat ID
```

### 3. 在config.yaml中引用

`config.yaml` 中已配置为从环境变量读取:

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"  # 从.env读取
  chat_id: "${TELEGRAM_CHAT_ID}"      # 从.env读取
```

### 如何获取Telegram信息

#### Bot Token
1. 在Telegram中找 @BotFather
2. 发送 `/newbot`
3. 按提示创建Bot
4. 复制Token

#### Chat ID
1. 在Telegram中找 @userinfobot
2. 发送任意消息
3. 复制返回的ID

---

## ✅ 安全检查清单

上传到GitHub前确保:
- [ ] `.env` 文件已被 `.gitignore` 忽略
- [ ] `config.yaml` 不包含真实Token
- [ ] 文档中没有泄露敏感信息

---

**当前状态**: ✅ 已清理，可安全上传
