# Week 1 - Learning Examples

**Author:** Leo Ji

这些是学习 LangGraph 的示例文件。

## ⚠️ 重要：环境变量设置

所有文件现在都从 `.env` 文件读取 API keys，不再硬编码。

**在运行任何文件之前，请确保项目根目录有 `.env` 文件：**

```bash
# .env 文件内容
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
POLYGON_API_KEY=your_polygon_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## 📁 文件列表

### 1. `first_simple_openai_agent.py`
最简单的 LangGraph agent
- 基础的聊天机器人
- 状态管理
- 消息流

### 2. `using_prebuilt.py`
使用预构建组件
- ToolNode
- tools_condition
- 内存管理

### 3. `add_tavily.py`
添加 Tavily 搜索工具
- 集成外部工具
- 工具调用
- BasicToolNode

### 4. `added_time_travel.py`
时间旅行功能
- 持久化内存
- 状态回溯

### 5. `add_customized_state.py`
自定义状态管理
- 扩展 State
- 人工干预
- Command 使用

## 🚀 运行示例

```bash
# 进入 Week1 目录
cd Week1

# 运行任何示例
python3 first_simple_openai_agent.py
```

## 📚 学习路径

建议按以下顺序学习：
1. `first_simple_openai_agent.py` - 基础
2. `using_prebuilt.py` - 预构建组件
3. `add_tavily.py` - 工具集成
4. `added_time_travel.py` - 持久化
5. `add_customized_state.py` - 高级状态管理

---

**注意：** 这些是学习示例，生产环境请使用项目根目录的 `agent_main.py`。

