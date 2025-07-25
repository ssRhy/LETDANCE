# LETDANCE - LangChain ConversationBufferMemory 版本

## 概述

这是 LETDANCE 心情记录应用的新版本，基于 LangChain 的 ConversationBufferMemory 实现，具备 AI 驱动的情绪分析和用户偏好学习能力。

## ✨ 核心特性

### 1. LangChain ConversationBufferMemory 集成

- **每用户独立记忆**：每个用户拥有独立的 ConversationBufferMemory 实例
- **持续学习**：系统持续记录用户的情绪反馈和 AI 分析结果
- **对话式记忆**：以对话形式存储用户心情和 AI 分析

### 2. AI 情绪分析 Agent

- **Azure OpenAI 驱动**：使用 GPT-4 进行专业情绪分析
- **多维分析**：
  - 核心情绪识别
  - 情绪关键词提取（3-4 个）
  - 用户情绪模式分析
  - 音乐风格推荐

### 3. 智能用户偏好学习

- **基于历史记录**：分析用户过往的情绪模式
- **动态适应**：根据累积数据调整分析策略
- **个性化建议**：提供个性化的音乐风格推荐

## 🏗️ 系统架构

```
EmotionAnalysisAgent
├── LLM (Azure OpenAI GPT-4)
├── ConversationBufferMemory (每用户独立)
├── 情绪分析提示模板
└── 用户偏好学习算法

Flask API
├── /api/mood (记录心情)
├── /api/mood/history (历史记录)
├── /api/user/insights (用户洞察)
└── /api/memory/summary (记忆摘要)
```

## 🚀 快速开始

### 1. 启动应用

```bash
python simple_flask_app.py
```

### 2. 访问界面

打开浏览器访问：http://localhost:5000

### 3. 使用流程

1. **选择心情**：从预设选项中选择或自定义输入
2. **AI 分析**：系统自动调用 GPT-4 进行情绪分析
3. **查看结果**：显示核心情绪、关键词、用户模式和音乐推荐
4. **记忆学习**：所有对话自动存储到 ConversationBufferMemory

## 🧠 ConversationBufferMemory 工作原理

### 记忆存储格式

```
用户消息: "心情记录: 今天工作压力很大，感觉焦虑不安"
AI消息: "分析结果 - 核心情绪: 焦虑, 关键词: 压力, 工作, 不安, 推荐音乐: ambient, calming"
```

### 学习机制

1. **累积分析**：每次分析都参考历史记录（最近 10 条）
2. **模式识别**：识别用户常见的情绪模式
3. **偏好调整**：根据历史数据调整推荐策略

## 📊 API 详细说明

### POST /api/mood

记录心情并进行 AI 分析

```json
{
  "user_id": "user_abc123",
  "mood": "今天心情不错，工作很顺利"
}
```

### GET /api/user/insights

获取用户洞察信息

```json
{
  "total_records": 15,
  "recent_analysis": "用户最近情绪稳定...",
  "memory_length": 30,
  "learning_status": "持续学习中"
}
```

### GET /api/memory/summary

获取 ConversationBufferMemory 摘要

```json
{
  "total_messages": 30,
  "recent_conversations": [
    { "type": "human", "content": "心情记录: ..." },
    { "type": "ai", "content": "分析结果 - ..." }
  ]
}
```

## 🎯 与之前版本的对比

| 特性     | 简单版本   | LangChain 版本           |
| -------- | ---------- | ------------------------ |
| 记忆系统 | 简单统计   | ConversationBufferMemory |
| 分析能力 | 关键词映射 | AI 深度分析              |
| 学习能力 | 频次统计   | 对话式记忆学习           |
| 个性化   | 基础推荐   | 智能模式识别             |
| 扩展性   | 有限       | 高度可扩展               |

## 🔧 配置说明

### Azure OpenAI 配置

在 `config/azure_config.py` 中配置：

- API Key
- Instance Name
- Deployment Name
- API Version

### 记忆设置

默认 ConversationBufferMemory 设置：

- `return_messages=True`：返回消息格式
- `memory_key="chat_history"`：记忆键名
- 历史分析限制：最近 10 条对话

## 🛡️ 安全特性

- **数据隔离**：每用户独立的记忆空间
- **错误处理**：完整的异常处理机制
- **默认值**：分析失败时提供默认结果
- **输入验证**：严格的输入数据验证

## 📈 未来扩展

1. **记忆持久化**：将 ConversationBufferMemory 持久化到数据库
2. **多模态分析**：集成图像和语音情绪分析
3. **群体洞察**：基于所有用户数据的群体情绪分析
4. **实时推荐**：基于当前状态的实时音乐生成

## 🐛 故障排除

### 常见问题

1. **Azure 连接失败**：检查网络和 API 配置
2. **分析超时**：检查 Azure OpenAI 服务状态
3. **记忆过载**：ConversationBufferMemory 会自动管理内存

### 调试模式

启动应用时自动开启调试模式，查看详细日志：

```
2025-07-17 21:39:56,603 - INFO - 初始化Azure OpenAI LLM，部署名称: gpt-4.1
2025-07-17 21:39:56,695 - INFO - 🎵 LETDANCE 心情记录应用启动 (基于LangChain ConversationBufferMemory)
```

## 📝 开发者说明

### 代码结构

- `EmotionAnalysisAgent`：核心分析引擎
- `ConversationBufferMemory`：用户记忆管理
- `Flask Routes`：API 接口层
- `情绪分析提示模板`：AI 分析指令

### 扩展指南

1. 继承`EmotionAnalysisAgent`类添加新功能
2. 修改提示模板以调整分析行为
3. 添加新的 API 端点扩展功能
4. 使用 LangChain 的其他记忆类型（如 ConversationSummaryMemory）

---

_基于 LangChain 0.3 构建，遵循官方最佳实践_ 🚀
