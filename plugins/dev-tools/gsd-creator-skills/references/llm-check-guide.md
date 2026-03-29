# LLM 可用性验证指南

> 由 `gsd-creator-skills` Phase 2 调用。当用户选择「需要 LLM」时，在生成 skill 模板之前必须先验证 LLM 服务可用性。

## 核心原则

| 原则 | 说明 |
|------|------|
| **静默测试** | 验证过程不在 CLI 中暴露原始错误堆栈或 HTTP 状态码 |
| **先测再走** | 验证通过后才进入模板生成阶段 |
| **友好反馈** | 失败时给出人类可读的修复建议，而非原始报错 |
| **YOLO 也阻塞** | 即使是 YOLO 模式，LLM 验证失败仍必须暂停 |

## 验证步骤

### 1. 识别所需 LLM 能力

询问用户（或从描述推断）：

| 维度 | 示例 |
|------|------|
| API 类型 | Claude API / OpenAI API / 其他 |
| 模型要求 | 是否需要特定模型 |
| 特殊能力 | function calling、vision、streaming 等 |

### 2. 执行静默测试

发送一个最小化请求（如简短 completion）：

- **成功** → 显示确认消息，继续下一阶段
- **失败** → 捕获错误，转换为人类可读的修复建议

### 3. 错误处理规范

**绝不在 CLI 中显示原始报错**（如 HTTP 429、ECONNREFUSED、stack trace 等）。

错误消息模板：

```
❌ LLM 可用性验证失败

问题：<人类可读的问题描述>
修复建议：
1. <具体步骤 1>
2. <具体步骤 2>
3. <具体步骤 3>

请修复后重试，或选择「不需要 LLM」继续创建。
```

### 常见错误 → 友好消息映射

| 原始错误 | 友好消息 |
|----------|----------|
| `ECONNREFUSED` / 网络超时 | 网络连接失败，请检查网络或代理配置 |
| `401 Unauthorized` | API 密钥未配置或已过期 |
| `429 Too Many Requests` | API 调用配额已用尽，请等待或升级计划 |
| `404 Model not found` | 指定模型不可用，请检查模型名称 |
| `500 Internal Server Error` | AI 服务暂时不可用，请稍后重试 |
| `ENVOENT` / 找不到模块 | SDK 未安装，请运行 npm install |

### 验证命令参考

```bash
# Claude API 验证
curl -s https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-haiku-4-5-20251001","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'

# OpenAI API 验证
curl -s https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model":"gpt-4o-mini","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
```

> 注意：以上命令仅用于验证连通性，实际执行时应由 Claude 自动运行并静默处理结果。
