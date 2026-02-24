# Assista 模型管理系统文档

## 概述

Assista支持灵活的大模型切换功能，可以自由切换云端和本地部署的模型，支持多种AI提供商。

## 支持的模型提供商

### 1. Coze Coding SDK (默认)
- Doubao Seed 1.8 (推荐)
- Doubao Seed 1.6
- Doubao Seed 1.6 Flash
- Doubao Seed 1.6 Thinking
- Doubao Seed 1.6 Vision
- Doubao Seed 1.6 Lite
- DeepSeek V3.2
- DeepSeek R1
- GLM-4-7
- Kimi K2

### 2. OpenAI
- GPT-4 Turbo
- GPT-4 Vision
- GPT-3.5 Turbo

### 3. Anthropic
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku

### 4. 本地模型
- LLaMA 3 (通过Ollama)
- Mistral (通过Ollama)
- 其他支持OpenAI兼容API的本地模型

### 5. 自定义
- 任何支持HTTP API的模型

## API 端点

### 获取所有模型
```bash
GET /api/models
```

响应示例：
```json
[
  {
    "id": "model_xxx",
    "name": "Doubao Seed 1.8",
    "provider": "coze",
    "modelId": "doubao-seed-1-8-251228",
    "status": "active",
    "isDefault": true,
    "priority": 1,
    "capabilities": {
      "streaming": true,
      "vision": true,
      "tools": true,
      "codeExecution": true,
      "maxTokens": 4096,
      "supportsCaching": true
    },
    "usageCount": 42,
    "totalTokens": 15230,
    "lastUsed": 1770915600000
  }
]
```

### 获取活动模型
```bash
GET /api/models?active=true
```

### 获取使用统计
```bash
GET /api/models?stats=true
```

### 设置活动模型
```bash
POST /api/models
Content-Type: application/json

{
  "action": "setActive",
  "modelId": "model_xxx"
}
```

### 测试模型连接
```bash
POST /api/models
Content-Type: application/json

{
  "action": "test",
  "modelId": "model_xxx"
}
```

### 添加新模型
```bash
POST /api/models
Content-Type: application/json

{
  "name": "GPT-4 Turbo",
  "provider": "openai",
  "modelId": "gpt-4-turbo-preview",
  "apiKey": "sk-...",
  "temperature": 0.7,
  "maxTokens": 4096,
  "capabilities": {
    "streaming": true,
    "vision": false,
    "tools": true,
    "codeExecution": false,
    "maxTokens": 4096,
    "supportsCaching": false
  },
  "priority": 20,
  "description": "OpenAI GPT-4 Turbo model"
}
```

### 更新模型配置
```bash
PUT /api/models
Content-Type: application/json

{
  "modelId": "model_xxx",
  "updates": {
    "temperature": 0.8,
    "maxTokens": 8192
  }
}
```

### 删除模型
```bash
DELETE /api/models?modelId=model_xxx
```

### 导出模型配置
```bash
GET /api/models/export
```

### 导入模型配置
```bash
POST /api/models
Content-Type: application/json

{
  "action": "import",
  "models": [...]
}
```

## 在Chat中使用指定模型

```bash
POST /api/chat
Content-Type: application/json

{
  "messages": [{"role": "user", "content": "Hello"}],
  "modelId": "model_xxx"  // 可选，不指定则使用活动模型
}
```

## Web界面使用

1. 访问 `http://localhost:5000`
2. 点击 **Models** 标签
3. 查看所有可用模型
4. 点击 **Activate** 切换到指定模型
5. 点击 **Test** 测试模型连接
6. 查看使用统计和成本

## 本地模型配置

### 使用Ollama

1. 安装Ollama:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

2. 下载模型:
```bash
ollama pull llama3:70b
ollama pull mistral:7b
```

3. 在Assista中添加模型:
```json
{
  "name": "Local LLaMA 3",
  "provider": "local",
  "modelId": "llama3:70b",
  "apiEndpoint": "http://localhost:11434/api/chat",
  "temperature": 0.7,
  "maxTokens": 4096,
  "capabilities": {
    "streaming": true,
    "vision": false,
    "tools": false,
    "codeExecution": false,
    "maxTokens": 4096,
    "supportsCaching": false
  },
  "priority": 40,
  "description": "Local LLaMA 3 70B via Ollama"
}
```

## 成本追踪

系统自动追踪每个模型的使用情况：

- 请求次数
- Token使用量
- 估算成本
- 平均延迟
- 错误率

## 最佳实践

1. **按任务选择模型**
   - 简单对话 → Flash/Lite模型
   - 复杂推理 → Thinking模型
   - 图像处理 → Vision模型
   - 长上下文 → Kimi K2

2. **成本优化**
   - 使用免费或低成本模型
   - 启用缓存功能
   - 限制maxTokens

3. **性能优化**
   - 本地模型用于隐私敏感任务
   - 云端模型用于复杂任务
   - 根据延迟要求选择

## 故障排除

### 模型测试失败
- 检查API密钥配置
- 验证API端点可访问
- 检查网络连接

### 本地模型不可用
- 确认Ollama正在运行
- 检查端口号（默认11434）
- 验证模型已下载

### 切换模型无效果
- 确认模型状态为"active"
- 检查API密钥是否配置
- 查看错误日志

## 高级配置

### 自定义API端点
对于支持OpenAI兼容API的模型，可以配置自定义端点：

```json
{
  "name": "Custom Model",
  "provider": "custom",
  "modelId": "custom-model",
  "apiEndpoint": "http://your-api-endpoint/v1/chat/completions",
  "apiKey": "your-api-key",
  ...
}
```

### 模型优先级
- 数字越小优先级越高
- 1-10: Coze内置模型
- 20-30: OpenAI/Anthropic
- 40-50: 本地模型
- 100+: 自定义模型

---

**Assista模型管理系统 - 灵活、强大、易于使用** 🚀
