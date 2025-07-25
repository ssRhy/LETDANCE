# LETDANCE

基于 LangChain 的智能舞蹈情感分析和音乐生成项目。

## 功能特性

- 🎥 **图像情感分析**: 使用 Azure OpenAI GPT-4V 分析图像中的情感表达
- 🕺 **姿态情感分析**: 基于拉班运动理论的实时姿态情感识别
- 🎵 **音乐关键词生成**: 智能汇总分析结果，生成音乐风格关键词
- 🤖 **LangChain 工作流**: 使用 AgentExecutor 协调整个分析流程

## 核心组件

### 工具（Tools）

- `ImageAnalysisTool`: 图像情感分析工具
- `PoseAnalysisTool`: 姿态情感分析工具（基于拉班理论）

### 主工作流（Main Workflow）

- `LetDanceWorkflow`: 主 Agent 执行器，协调所有分析步骤

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

确保在 `config.py` 中配置了正确的 Azure OpenAI credentials。

### 3. 运行主工作流

```python
from main_agent import LetDanceWorkflow

# 创建工作流实例
workflow = LetDanceWorkflow()

# 执行完整分析流程（分析10秒）
result = workflow.run_complete_workflow(duration=10)

# 查看结果
if result['success']:
    print(f"生成的音乐关键词: {result['final_keywords']}")
else:
    print(f"分析失败: {result['message']}")
```

### 4. 使用主函数

```bash
python main_agent.py
```

## 工作流程

1. **图像分析阶段**

   - 从摄像头拍照
   - 使用 Azure OpenAI 分析图像情感
   - 提取情感特征

2. **姿态分析阶段**

   - 实时检测人体姿态关键点
   - 基于拉班运动理论分析情感
   - 识别 7 种情感状态

3. **音乐关键词生成**

   - 汇总图像和姿态分析结果
   - 智能提取 4 个音乐风格关键词
   - 为音乐生成提供输入

4. **音乐生成（预留）**
   - 接收音乐关键词
   - 调用音乐生成模型（待实现）

## 项目结构

```
LETDANCE/
├── main_agent.py          # 主Agent执行器
├── config.py              # 项目配置
├── camera_manager.py      # 摄像头管理
├── tools/                 # LangChain工具
│   ├── __init__.py
│   ├── image_analysis_tool.py
│   ├── pose_analysis_tool.py
│   └── registry.py
└── requirements.txt       # 依赖包
```

## 技术栈

- **LangChain 0.3**: Agent 框架和工具管理
- **Azure OpenAI GPT-4V**: 图像情感分析
- **YOLO**: 人体姿态检测
- **OpenCV**: 摄像头和图像处理
- **拉班运动理论**: 姿态情感分析

## 注意事项

- 确保摄像头连接正常
- 需要稳定的网络连接访问 Azure OpenAI
- 项目专注于实时处理，不保存任何本地文件
- 代码保持简洁，遵循单一职责原则
