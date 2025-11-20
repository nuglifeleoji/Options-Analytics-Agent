
import sqlite3
from typing import Annotated
from typing_extensions import TypedDict
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

# Import rules loader
from utils.rules_loader import load_agent_rules

# Import configuration and tools (same as agent_main.py)
from config import settings, PATHS, LIMITS

# Import all tools
from tools.search import search_options, batch_search_options
from tools.export import make_option_table, plot_options_chain
from tools.web_search import toolTavilySearch, human_assistance
from tools.code_execution import code_execution_tool
from tools.analysis import analysis_tools
from monitoring.performance_monitor import get_performance_stats, monitor

# Import RAG tools
import sys
from pathlib import Path
rag_path = Path(__file__).parent / "rag"
if str(rag_path) not in sys.path:
    sys.path.insert(0, str(rag_path))

try:
    from rag_collection_tools import (
        collect_and_store_options,
        batch_collect_options,
        collect_date_range,
        check_missing_data,
        auto_update_watchlist
    )
    from rag_tools import (
        store_options_data,
        search_knowledge_base,
        get_historical_options,
        get_snapshot_by_id,
        detect_anomaly
    )
    collection_tools = [
        collect_and_store_options, batch_collect_options,
        collect_date_range, check_missing_data, auto_update_watchlist
    ]
    rag_tools_list = [
        store_options_data, search_knowledge_base,
        get_historical_options, get_snapshot_by_id, detect_anomaly
    ]
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  RAG tools not available: {e}")
    collection_tools = []
    rag_tools_list = []
    RAG_AVAILABLE = False

# ============================================================================
# Initialize
# ============================================================================
print("=" * 70)
print("🤖 Initializing Agent with Dynamic Rules")
print("=" * 70)
print()

settings.initialize()

# Assemble tools
tools = [
    search_options, batch_search_options,
    make_option_table, plot_options_chain,
    human_assistance, toolTavilySearch,
    code_execution_tool, get_performance_stats,
    *collection_tools, *rag_tools_list, *analysis_tools
]

print(f"✅ Loaded {len(tools)} tools")

# Initialize LLM
llm = init_chat_model(settings.model.MODEL_NAME, model_provider=settings.model.MODEL_PROVIDER)
llm_with_tools = llm.bind_tools(tools)
print(f"✅ Model: {settings.model.MODEL_NAME}")

# Setup memory
db_path = PATHS.CONVERSATION_MEMORY_DB
conn = sqlite3.connect(db_path, check_same_thread=False)
memory = SqliteSaver(conn)
print(f"✅ Memory: {db_path}")

# ============================================================================
# 🆕 LOAD RULES FROM FILES (Not hardcoded!)
# ============================================================================
print()
print("=" * 70)
print("📚 Loading Rules from Files")
print("=" * 70)
print()

# Load main agent rules
print("📖 Loading: agent_rules.md")
agent_rules = load_agent_rules("agent_rules.md", as_system_prompt=False)
print(f"   ✅ Loaded: {len(agent_rules)} characters")

# Load specialized analysis rules
print("📖 Loading: analysis_rules.md")
analysis_rules = load_agent_rules("analysis_rules.md", as_system_prompt=False)
print(f"   ✅ Loaded: {len(analysis_rules)} characters")

# Combine rules
SYSTEM_PROMPT = f"""
{agent_rules}

---

# 📊 SPECIALIZED ANALYSIS RULES

{analysis_rules}

---

**Note**: This agent uses modular rules loaded from external files:
- `rules/agent_rules.md` - Core behaviors and skills
- `rules/analysis_rules.md` - Professional analysis methodology

To modify agent behavior, edit the corresponding markdown files.
"""

print()
print(f"✅ Total rules loaded: {len(SYSTEM_PROMPT)} characters")
print(f"   📁 agent_rules.md: Core skills and workflows")
print(f"   📁 analysis_rules.md: Professional analysis methodology")
print()

# ============================================================================
# Define State and Graph
# ============================================================================
class State(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot(state: State):
    """Chatbot node with context management."""
    messages = state["messages"]
    
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    # Context management
    MAX_MESSAGES = LIMITS.MAX_MESSAGES
    if len(messages) > MAX_MESSAGES + 1:
        print(f"⚠️  Context too long. Truncating to last {MAX_MESSAGES}...")
        system_msg = messages[0] if isinstance(messages[0], SystemMessage) else SystemMessage(content=SYSTEM_PROMPT)
        recent_messages = messages[-(MAX_MESSAGES):]
        filtered_messages = []
        
        for i, msg in enumerate(recent_messages):
            if hasattr(msg, 'type') and msg.type == 'tool':
                if i > 0 and hasattr(recent_messages[i-1], 'tool_calls') and recent_messages[i-1].tool_calls:
                    filtered_messages.append(msg)
                else:
                    continue
            else:
                filtered_messages.append(msg)
        
        messages = [system_msg] + filtered_messages
        print(f"✅ Context truncated to {len(messages)} messages.")
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# Build graph
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

graph = graph_builder.compile(checkpointer=memory)
config = {"configurable": {"thread_id": "1"}}

print("=" * 70)
print("✅ Graph Compiled!")
print("=" * 70)
print()

# ============================================================================
# Stream Function
# ============================================================================
def stream_graph_updates(user_input: str):
    """Process user input with performance tracking."""
    monitor.start_tracking(user_input)
    
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}, config):
        for value in event.values():
            if isinstance(value, dict) and "messages" in value:
                message = value["messages"][-1]
                if hasattr(message, 'content'):
                    print("Assistant:", message.content)
                
                if hasattr(message, 'response_metadata'):
                    metadata = message.response_metadata
                    if 'token_usage' in metadata:
                        token_usage = metadata['token_usage']
                        monitor.record_tokens(
                            token_usage.get('prompt_tokens', 0),
                            token_usage.get('completion_tokens', 0)
                        )
                
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        monitor.record_tool_usage(tool_call.get('name', 'unknown'))
    
    monitor.stop_tracking()

# ============================================================================
# Main Loop
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("✨ AGENT WITH MODULAR RULES ✨")
    print("=" * 70)
    print()
    print("💡 Features:")
    print("   • Rules loaded from multiple markdown files")
    print("   • Easy to update without changing code")
    print("   • Version controlled")
    print("   • Modular and specialized")
    print()
    print("📚 Active Rule Modules:")
    print("   📄 agent_rules.md - Core skills and workflows")
    print("   📄 analysis_rules.md - Professional analysis methodology")
    print()
    print("🔧 To update rules:")
    print("   1. Edit any .md file in rules/ directory")
    print("   2. Restart this script")
    print("   3. Rules automatically reload!")
    print()
    print("=" * 70)
    print(f"🤖 Model: {settings.model.MODEL_NAME}")
    print(f"💾 Memory: {db_path}")
    print(f"🔧 Tools: {len(tools)}")
    print(f"📚 Rules: Loaded from 2 external files")
    print("=" * 70)
    print()
    print("Type 'quit', 'exit', or 'q' to exit")
    print("=" * 70)
    print()
    
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye! 👋")
            break
        stream_graph_updates(user_input)

