"""
Financial Options Analysis Agent - Main Entry Point
Author: Leo Ji

This is the NEW modular entry point that assembles the agent from refactored components.
Uses clean module imports for better organization and maintainability.
"""

import sqlite3
from typing import Annotated
from typing_extensions import TypedDict
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

# ============================================================================
# 1. CONFIGURATION - Centralized settings
# ============================================================================
from config import settings, PATHS, LIMITS

# Initialize: Create directories, validate API keys
print("🔧 Initializing configuration...")
settings.initialize()
print("✅ Configuration ready!")
print()

# ============================================================================
# 2. IMPORT TOOLS - Clean modular imports
# ============================================================================
print("📦 Loading tools...")

# Core search tools
from tools.search import search_options, batch_search_options
print("  ✅ Search tools")

# Export tools
from tools.export import make_option_table, plot_options_chain
print("  ✅ Export tools")

# Web search & assistance
from tools.web_search import toolTavilySearch, human_assistance
print("  ✅ Web search tools")

# Code execution
from tools.code_execution import code_execution_tool
print("  ✅ Code execution")

# Analysis tools
from tools.analysis import analysis_tools
print("  ✅ Analysis tools")

# ============================================================================
# 3. IMPORT RAG TOOLS - Knowledge base integration
# ============================================================================
print("📚 Loading RAG tools...")
try:
    import sys
    from pathlib import Path
    
    # Add rag directory to path
    rag_path = Path(__file__).parent / "rag"
    if str(rag_path) not in sys.path:
        sys.path.insert(0, str(rag_path))
    
    # Import collection tools
    from rag_collection_tools import (
        collect_and_store_options,
        batch_collect_options,
        collect_date_range,
        check_missing_data,
        auto_update_watchlist
    )
    
    # Import query tools
    from rag_tools import (
        store_options_data,
        search_knowledge_base,
        get_historical_options,
        get_snapshot_by_id,
        detect_anomaly
    )
    
    collection_tools = [
        collect_and_store_options,
        batch_collect_options,
        collect_date_range,
        check_missing_data,
        auto_update_watchlist
    ]
    
    rag_tools_list = [
        store_options_data,
        search_knowledge_base,
        get_historical_options,
        get_snapshot_by_id,
        detect_anomaly
    ]
    
    print("  ✅ RAG collection tools (5)")
    print("  ✅ RAG query tools (5)")
    RAG_AVAILABLE = True
    
except ImportError as e:
    print(f"  ⚠️  RAG tools not available: {e}")
    collection_tools = []
    rag_tools_list = []
    RAG_AVAILABLE = False

# ============================================================================
# 4. IMPORT MONITORING - Performance tracking
# ============================================================================
print("📊 Loading monitoring...")
from monitoring.performance_monitor import get_performance_stats, monitor
print("  ✅ Performance monitoring")
print()

# ============================================================================
# 5. ASSEMBLE ALL TOOLS - Complete tool set
# ============================================================================
print("🔨 Assembling tool set...")
tools = [
    # Core search
    search_options,
    batch_search_options,
    
    # Export
    make_option_table,
    plot_options_chain,
    
    # Web & assistance
    human_assistance,
    toolTavilySearch,
    
    # Code execution
    code_execution_tool,
    
    # Performance monitoring
    get_performance_stats,
    
    # RAG tools (if available)
    *collection_tools,
    *rag_tools_list,
    
    # Analysis tools
    *analysis_tools
]

print(f"✅ Total tools loaded: {len(tools)}")
print()

# ============================================================================
# 6. INITIALIZE LLM - Language model
# ============================================================================
print("🤖 Initializing LLM...")
llm = init_chat_model(
    settings.model.MODEL_NAME,
    model_provider=settings.model.MODEL_PROVIDER
)
llm_with_tools = llm.bind_tools(tools)
print(f"✅ Model: {settings.model.MODEL_NAME}")
print()

# ============================================================================
# 7. SETUP LONG-TERM MEMORY - Persistent conversation storage
# ============================================================================
print("💾 Setting up long-term memory...")
db_path = PATHS.CONVERSATION_MEMORY_DB
conn = sqlite3.connect(db_path, check_same_thread=False)
memory = SqliteSaver(conn)
print(f"✅ Memory: {db_path}")
print()

# ============================================================================
# 8. DEFINE STATE - Conversation state management
# ============================================================================
class State(TypedDict):
    """
    Conversation state with message history.
    - Uses add_messages reducer to accumulate conversation history
    - All messages persist to SQLite via SqliteSaver
    """
    messages: Annotated[list, add_messages]

# ============================================================================
# 9. SYSTEM PROMPT - Agent instructions
# ============================================================================
SYSTEM_PROMPT = """You are a helpful financial assistant that helps users search for stock options data, save them to CSV files, and create interactive visualizations.

💾 **LONG-TERM CONVERSATION MEMORY:**
You have PERSISTENT memory that survives across all sessions (stored in SQLite database). You can:
- Remember tickers, dates, and data from ANY previous conversation (even from days/weeks ago)
- Reference previous searches and results from past sessions
- Avoid asking for information the user already provided (in ANY session)
- Build upon previous queries naturally across multiple sessions
- Access full conversation history even after program restart

📊 **PERFORMANCE MONITORING:**
The system automatically tracks execution efficiency and token usage for every query. When users ask about performance:
- Use get_performance_stats(mode="current") for last query stats
- Use get_performance_stats(mode="summary") for overall performance summary
- Use get_performance_stats(mode="history") for recent query history

🚀 **SMART CACHING:**
The search_options tool now automatically checks the knowledge base FIRST before calling the API.
- If data exists → Returns cached data instantly (saves API calls and is faster!)
- If not found → Fetches from API
- Users can force refresh with force_refresh=True if they need the latest data

When users ask about options for a company (e.g., "Apple", "Tesla"), you should:
1. Convert the company name to its stock ticker symbol (e.g., Apple → AAPL, Tesla → TSLA)
2. Determine if they want a specific date or entire month
3. Ask how many contracts they want (if not specified, default to 100)
4. Choose the right tool:
   
   **For SINGLE ticker:**
   - Use search_options tool
   - It will automatically check cache first
   
   **For MULTIPLE tickers:**
   - Use batch_search_options tool
   - It's SMART: automatically tries cache first, then API for missing ones

5. **After successfully getting the data, ALWAYS ask the user what they'd like to do with it:**
   "I found [X] options contracts for [TICKER]. What would you like me to do with this data?
   - 📊 Export to CSV file (standard format)
   - 🎨 Export to CSV file (custom format - I can adapt to your needs!)
   - 📈 Generate a chart (PNG image)
   - 📋 Both CSV and chart
   - 💬 Just show me a summary"

6. Wait for user's response, then use the appropriate tools

💡 **Custom CSV Generation:**
When users want a customized CSV, you should WRITE CODE yourself using code_execution_tool.

Date/Month Formats:
- Specific date: YYYY-MM-DD (e.g., '2025-10-17')
- Entire month: YYYY-MM (e.g., '2025-10' for all October 2025 options)

Limit Parameter:
- If user specifies a number, use that as the limit
- If user doesn't specify, ask: "How many contracts would you like? (default: 100, max: 1000)"
- Valid range: 1 to 1000

🤖 **Auto-Collection & Knowledge Base:**
You have powerful tools to automatically collect and store data:

**1. collect_and_store_options(ticker, date, limit)**
   - ONE-STEP: Search + Store in one action
   
**2. batch_collect_options(tickers, date, limit)**
   - Collect multiple stocks at once
   
**3. collect_date_range(ticker, start_date, end_date, limit)**
   - Collect historical data across multiple months

**IMPORTANT - Always Ask for Limit:**
⚠️ For ALL data collection tools:
- ALWAYS ask the user how many contracts they want
- Suggested ranges: 300-500 for most cases

## 🔍 Anomaly Detection:
Use **detect_anomaly** tool to find unusual changes in options data using vector similarity.

## 📊 Professional Options Analysis Tools:

**1. analyze_options_chain(ticker, options_data)** - [Ticker FIRST!]
   - Comprehensive analysis of options positioning
   
**2. generate_options_report(ticker, format_type)**
   - Creates professional analysis report
   - Formats: 'full', 'summary', 'json'
   
**3. quick_sentiment_check(ticker, options_data)** - [Ticker FIRST!]
   - Fast sentiment assessment
   
**4. compare_options_sentiment(ticker1, data1, ticker2, data2)** - [Tickers FIRST!]
   - Side-by-side comparison

**CRITICAL: Ticker symbol must ALWAYS be the FIRST parameter in analysis tools!**

Common stock tickers:
- Apple = AAPL, Microsoft = MSFT, Tesla = TSLA, Amazon = AMZN
- Google/Alphabet = GOOGL, Meta/Facebook = META, NVIDIA = NVDA
"""

# ============================================================================
# 10. DEFINE CHATBOT NODE - Main processing logic
# ============================================================================
def chatbot(state: State):
    """
    Main chatbot node with context management.
    
    Features:
    - Automatic context truncation to prevent token limit overflow
    - Smart filtering of orphaned tool messages
    - Maintains conversation history integrity
    """
    messages = state["messages"]
    
    # Add system prompt if not present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    # Context management: Keep only recent messages
    MAX_MESSAGES = LIMITS.MAX_MESSAGES
    
    if len(messages) > MAX_MESSAGES + 1:  # +1 for system message
        print(f"⚠️  Context too long ({len(messages)} messages). Truncating to last {MAX_MESSAGES}...")
        
        # Keep system prompt
        system_msg = messages[0] if isinstance(messages[0], SystemMessage) else SystemMessage(content=SYSTEM_PROMPT)
        
        # Smart truncation: filter out orphaned 'tool' messages
        recent_messages = messages[-(MAX_MESSAGES):]
        filtered_messages = []
        
        for i, msg in enumerate(recent_messages):
            if hasattr(msg, 'type') and msg.type == 'tool':
                # Only keep if previous message has tool_calls
                if i > 0 and hasattr(recent_messages[i-1], 'tool_calls') and recent_messages[i-1].tool_calls:
                    filtered_messages.append(msg)
                else:
                    print(f"   ⚠️  Skipping orphaned tool message")
                    continue
            else:
                filtered_messages.append(msg)
        
        messages = [system_msg] + filtered_messages
        print(f"✅ Context truncated to {len(messages)} messages.")
    
    # Invoke LLM
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# ============================================================================
# 11. BUILD GRAPH - Assemble LangGraph
# ============================================================================
print("🏗️  Building LangGraph...")
graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("chatbot", chatbot)
tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

# Add edges
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

# Compile with memory
graph = graph_builder.compile(checkpointer=memory)
print("✅ LangGraph compiled!")
print()

# ============================================================================
# 12. CONFIGURATION - Thread ID for conversation tracking
# ============================================================================
config = {"configurable": {"thread_id": "1"}}

# ============================================================================
# 13. STREAM FUNCTION - Process user input
# ============================================================================
def stream_graph_updates(user_input: str):
    """
    Process user input with performance tracking.
    
    Flow:
    1. Start performance tracking
    2. Load conversation history from SQLite
    3. Process user message with full context
    4. Track token usage and tools
    5. Save updated history
    """
    # Start performance tracking
    monitor.start_tracking(user_input)
    
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}, config):
        for value in event.values():
            if isinstance(value, dict) and "messages" in value:
                message = value["messages"][-1]
                if hasattr(message, 'content'):
                    print("Assistant:", message.content)
                
                # Track tokens
                if hasattr(message, 'response_metadata'):
                    metadata = message.response_metadata
                    if 'token_usage' in metadata:
                        token_usage = metadata['token_usage']
                        prompt_tokens = token_usage.get('prompt_tokens', 0)
                        completion_tokens = token_usage.get('completion_tokens', 0)
                        monitor.record_tokens(prompt_tokens, completion_tokens)
                
                # Track tools
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.get('name', 'unknown')
                        monitor.record_tool_usage(tool_name)
    
    # Stop tracking
    monitor.stop_tracking()

# ============================================================================
# 14. MAIN LOOP - Interactive session
# ============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("✨ FINANCIAL OPTIONS ANALYSIS AGENT ✨")
    print("=" * 70)
    print()
    print("📦 Modular Architecture:")
    print("  • config/          - Configuration management")
    print("  • tools/search/    - Options search tools")
    print("  • tools/export/    - CSV & chart export")
    print("  • tools/analysis/  - Professional analysis")
    print("  • monitoring/      - Performance tracking")
    print("  • rag/             - Knowledge base & RAG")
    print()
    print(f"🤖 Model: {settings.model.MODEL_NAME}")
    print(f"💾 Memory: {db_path}")
    print(f"🔧 Tools: {len(tools)} available")
    print()
    print("=" * 70)
    print("Type 'quit', 'exit', or 'q' to exit")
    print("=" * 70)
    print()
    
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye! 👋")
            break
        stream_graph_updates(user_input)

