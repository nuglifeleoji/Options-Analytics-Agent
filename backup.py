import os
import requests
import json
import csv
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from typing import Annotated
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

@tool
def human_assistance(query: str) -> str:
    """Request assistance from a human."""
    human_response = interrupt({"query": query})
    return human_response["data"]

@tool
def search_options(ticker: str, date: str, limit: int = 300, force_refresh: bool = False) -> str:
    """Search for options data for a given stock ticker and expiration date or month.
    
    This tool now has smart caching: it first checks the knowledge base for existing data.
    If data exists and is recent, it returns cached data instead of calling the API.
    This saves API calls and provides faster responses.
    
    Args:
        ticker: Stock symbol (e.g., 'AAPL', 'TSLA')
        date: Expiration date in YYYY-MM-DD format (e.g., '2025-01-17') 
              OR month in YYYY-MM format (e.g., '2025-10' for all October 2025 options)
        limit: Maximum number of contracts to return (default: 100, max: 1000)
        force_refresh: If True, skip cache and fetch fresh data from API (default: False)
    
    Returns:
        JSON string with options data including contract details
    """
    if not force_refresh:
        try:
            from rag.rag_knowledge_base import query_sqlite
            print(f"🔍 Checking knowledge base for {ticker} {date}...")

            cached_data = query_sqlite(
                ticker=ticker.upper(),
                start_date=date,
                end_date=date,
                limit=1
            )
            
            if cached_data:
                cached_snapshot = cached_data[0]
                cached_json = cached_snapshot['data']
                cached_count = cached_json.get('count', 0)
                
                if cached_count >= limit:
                    print(f"✅ Found in knowledge base! ({cached_count} contracts)")
                    print(f"📦 Using cached data from {cached_snapshot['timestamp']}")
                    if cached_count > limit:
                        results = cached_json.get('results', [])[:limit]
                        cached_json['results'] = results
                        cached_json['count'] = len(results)
                        cached_json['note'] = f"Returned {limit} of {cached_count} cached contracts"
                    
                    cached_json['from_cache'] = True
                    cached_json['cached_at'] = cached_snapshot['timestamp']
                    
                    return json.dumps(cached_json)
                else:
                    print(f"⚠️ Cached data only has {cached_count} contracts, need {limit}")
                    print(f"📡 Fetching fresh data from API...")
            else:
                print(f"📭 No cached data found")
                print(f"📡 Fetching from API...")
                
        except ImportError:
            print("⚠️ RAG module not available, fetching from API...")
        except Exception as e:
            print(f"⚠️ Error checking cache: {e}")
            print(f"📡 Fetching from API...")
    else:
        print(f"🔄 Force refresh requested, fetching fresh data from API...")
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        return json.dumps({"error": "POLYGON_API_KEY not found in environment variables"})
    
    url = "https://api.polygon.io/v3/reference/options/contracts"
    
    # Use params dict instead of URL string concatenation (avoids 400 error)
    params = {
        "underlying_ticker": ticker.upper(),
        "limit": 1000,
        "apiKey": api_key
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        all_contracts = data.get('results', [])
        
        # Check if date is a month (YYYY-MM) or specific date (YYYY-MM-DD)
        if len(date) == 7:  # Month format: YYYY-MM
            # Filter by month
            filtered = [c for c in all_contracts if c.get('expiration_date', '').startswith(date)]
            print(f"[DEBUG] Searching for all options in month: {date}")
        else:  # Specific date format: YYYY-MM-DD
            # Filter by exact date
            filtered = [c for c in all_contracts if c.get('expiration_date') == date]
            print(f"[DEBUG] Searching for options on specific date: {date}")
        
        print(f"[DEBUG] Total contracts fetched: {len(all_contracts)}")
        print(f"[DEBUG] Contracts matching criteria: {len(filtered)}")
        
        # Limit the results to requested number
        limited_results = filtered[:limit] if len(filtered) > limit else filtered
        
        if filtered:
            return json.dumps({
                "results": limited_results, 
                "count": len(limited_results),
                "total_available": len(filtered),
                "message": f"Showing {len(limited_results)} of {len(filtered)} contracts"
            })
        else:
            return json.dumps({
                "results": [], 
                "count": 0, 
                "total_available": 0,
                "message": f"No options found for {ticker} with date/month: {date}"
            })
    else:
        return json.dumps({"error": f"Error: {response.status_code}"})

@tool
def batch_search_options(tickers: str, date: str, limit: int = 300) -> str:
    """Smart batch search for multiple tickers with automatic cache fallback.
    
    This tool intelligently searches for options data for multiple tickers:
    1. First checks the knowledge base for each ticker
    2. For tickers found in cache → returns cached data
    3. For tickers NOT found → automatically fetches from API
    4. Optionally stores newly fetched data
    5. Returns combined results
    
    Args:
        tickers: Comma-separated ticker symbols (e.g., 'AAPL,MSFT,TSLA,GOOGL')
        date: Date or month (e.g., '2025-11' or '2025-11-07')
        limit: Contracts per ticker (default: 300)
    
    Returns:
        Summary with cache hits, API fetches, and combined results
    
    Example:
        batch_search_options("AAPL,MSFT,TSLA", "2025-11", 300)
    """
    try:
        # 解析 tickers
        ticker_list = [t.strip().upper() for t in tickers.split(',')]
        
        print(f"\n🔍 Batch searching {len(ticker_list)} tickers for {date}...")
        print(f"Tickers: {', '.join(ticker_list)}\n")
        
        results = {
            'cache_hits': [],      # 从缓存获取的
            'api_fetches': [],     # 需要API获取的
            'failed': [],          # 失败的
            'data': {}             # 所有数据
        }
        
        # 步骤1: 检查每个ticker的缓存
        print("="*70)
        print("📦 STEP 1: Checking cache...")
        print("="*70)
        
        for ticker in ticker_list:
            try:
                from rag.rag_knowledge_base import query_sqlite
                
                cached = query_sqlite(
                    ticker=ticker,
                    start_date=date,
                    end_date=date,
                    limit=1
                )
                
                if cached and cached[0]['total_contracts'] >= limit:
                    # 找到缓存
                    print(f"✅ {ticker:6} - Cache HIT ({cached[0]['total_contracts']} contracts)")
                    results['cache_hits'].append(ticker)
                    
                    # 获取数据
                    cached_data = cached[0]['data']
                    if cached_data.get('count', 0) > limit:
                        cached_data['results'] = cached_data['results'][:limit]
                        cached_data['count'] = limit
                    
                    cached_data['from_cache'] = True
                    cached_data['source'] = 'knowledge_base'
                    results['data'][ticker] = cached_data
                else:
                    # 缓存未命中
                    print(f"📭 {ticker:6} - Cache MISS (will fetch from API)")
                    results['api_fetches'].append(ticker)
                    
            except Exception as e:
                print(f"⚠️  {ticker:6} - Cache check failed: {e}")
                results['api_fetches'].append(ticker)
                
        if results['api_fetches']:
            print(f"\n{'='*70}")
            print(f"📡 STEP 2: Fetching {len(results['api_fetches'])} tickers from API...")
            print("="*70)
            
            for ticker in results['api_fetches']:
                try:
                    print(f"🔄 Fetching {ticker}...")
                    
                    # 调用 search_options（会自动尝试缓存）
                    data_str = search_options.invoke({
                        "ticker": ticker, 
                        "date": date, 
                        "limit": limit,
                        "force_refresh": True 
                    })
                    
                    data = json.loads(data_str)
                    
                    if "error" in data:
                        print(f"❌ {ticker:6} - Failed: {data['error']}")
                        results['failed'].append(ticker)
                    elif data.get('count', 0) == 0:
                        print(f"⚠️  {ticker:6} - No data found")
                        results['failed'].append(ticker)
                    else:
                        print(f"✅ {ticker:6} - Fetched {data['count']} contracts")
                        data['from_cache'] = False
                        data['source'] = 'api'
                        results['data'][ticker] = data
                        
                        # 可选：自动存储到知识库
                        try:
                            from rag.rag_tools import store_options_data
                            print(f"   💾 Auto-saving to knowledge base...")
                            store_options_data.invoke({
                                "data": data_str,
                                "ticker": ticker,
                                "date": date
                            })
                            print(f"   ✅ Saved!")
                        except Exception as e:
                            print(f"   ⚠️  Save failed: {e}")
                    
                    # 避免API限流
                    import time
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"❌ {ticker:6} - Error: {str(e)}")
                    results['failed'].append(ticker)
        
        # 步骤3: 生成摘要
        print(f"\n{'='*70}")
        print("📊 BATCH SEARCH SUMMARY")
        print("="*70)
        
        summary = f"""
🔍 Batch Search Complete for {date}

📈 Results:
  • Total Tickers: {len(ticker_list)}
  • From Cache: {len(results['cache_hits'])} ✅
  • From API: {len([t for t in results['api_fetches'] if t not in results['failed']])} 📡
  • Failed: {len(results['failed'])} ❌

"""
        
        if results['cache_hits']:
            summary += f"\n✅ Cache Hits ({len(results['cache_hits'])}):\n"
            for ticker in results['cache_hits']:
                count = results['data'][ticker].get('count', 0)
                summary += f"  • {ticker}: {count} contracts\n"
        
        if results['api_fetches'] and len([t for t in results['api_fetches'] if t not in results['failed']]) > 0:
            summary += f"\n📡 API Fetches ({len([t for t in results['api_fetches'] if t not in results['failed']])}):\n"
            for ticker in results['api_fetches']:
                if ticker not in results['failed'] and ticker in results['data']:
                    count = results['data'][ticker].get('count', 0)
                    summary += f"  • {ticker}: {count} contracts (auto-saved to KB)\n"
        
        if results['failed']:
            summary += f"\n❌ Failed ({len(results['failed'])}):\n"
            for ticker in results['failed']:
                summary += f"  • {ticker}\n"
        
        # 统计总合约数
        total_contracts = sum(d.get('count', 0) for d in results['data'].values())
        summary += f"\n📊 Total Contracts Retrieved: {total_contracts:,}\n"
        
        # 添加数据可用性信息
        summary += f"\n💡 All data is now available in the knowledge base for future queries!\n"
        
        return summary
        
    except Exception as e:
        return f"❌ Error in batch search: {str(e)}"


@tool
def make_option_table(data: str, ticker: str) -> str:
    """Convert options data to a CSV file and save it.
    
    Args:
        data: JSON string containing options data from search_options tool
        ticker: Stock ticker symbol (e.g., 'AAPL') for naming the file
    
    Returns:
        Success message with the CSV filename
    """
    try:
        # Parse the JSON data
        options_data = json.loads(data)
        
        # Check if we have results
        if "results" not in options_data or not options_data["results"]:
            return "No options data found to export."
        
        contracts = options_data["results"]
        
        # Try to extract expiration date from first contract for better filename
        first_exp_date = contracts[0].get('expiration_date', '') if contracts else ''
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create descriptive filename based on expiration dates
        if first_exp_date:
            # Extract year-month from first contract
            exp_month = first_exp_date[:7]  # YYYY-MM
            filename = f"{ticker}_options_{exp_month}_{timestamp}.csv"
        else:
            filename = f"{ticker}_options_{timestamp}.csv"
        
        # Define CSV columns with better formatting
        fieldnames = [
            "Ticker Symbol",
            "Contract Type",
            "Strike Price",
            "Expiration Date",
            "Shares per Contract",
            "Primary Exchange",
            "Exercise Style",
            "Underlying Ticker"
        ]
        
        # Write to CSV file
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for contract in contracts:
                # Format contract type
                contract_type = contract.get("contract_type", "N/A")
                if contract_type != "N/A":
                    contract_type = contract_type.upper()  # CALL or PUT
                
                row = {
                    "Ticker Symbol": contract.get("ticker", "N/A"),
                    "Contract Type": contract_type,
                    "Strike Price": f"${contract.get('strike_price', 'N/A')}" if contract.get('strike_price') else "N/A",
                    "Expiration Date": contract.get("expiration_date", "N/A"),
                    "Shares per Contract": contract.get("shares_per_contract", "N/A"),
                    "Primary Exchange": contract.get("primary_exchange", "N/A"),
                    "Exercise Style": contract.get("exercise_style", "N/A"),
                    "Underlying Ticker": contract.get("underlying_ticker", ticker.upper())
                }
                writer.writerow(row)
        
        return f"✅ Successfully saved {len(contracts)} options contracts to CSV file: {filename}"
        
    except json.JSONDecodeError:
        return "❌ Error: Invalid JSON data provided"
    except Exception as e:
        return f"❌ Error creating CSV file: {str(e)}"

@tool
def plot_options_chain(data: str, ticker: str) -> str:
    """Create a butterfly chart (symmetric horizontal bar chart) showing options distribution.
    
    Args:
        data: JSON string containing options data from search_options tool
        ticker: Stock ticker symbol (e.g., 'AAPL') for chart title
    
    Returns:
        Success message with the chart filename (PNG image)
    """
    try:
        # Parse the JSON data
        options_data = json.loads(data)
        
        # Check if we have results
        if "results" not in options_data or not options_data["results"]:
            return "No options data found to plot."
        
        contracts = options_data["results"]
        
        # Count contracts by strike price and type
        calls_dict = {}
        puts_dict = {}
        
        for contract in contracts:
            strike = contract.get('strike_price')
            contract_type = contract.get('contract_type', '').lower()
            
            if strike and contract_type:
                if contract_type == 'call':
                    calls_dict[strike] = calls_dict.get(strike, 0) + 1
                elif contract_type == 'put':
                    puts_dict[strike] = puts_dict.get(strike, 0) + 1
        
        if not calls_dict and not puts_dict:
            return "No valid options data to plot (missing strike prices or contract types)."
        
        # Get all unique strike prices and sort them
        all_strikes = sorted(set(list(calls_dict.keys()) + list(puts_dict.keys())))
        
        # Prepare data for butterfly chart
        call_counts = [calls_dict.get(strike, 0) for strike in all_strikes]
        put_counts = [puts_dict.get(strike, 0) for strike in all_strikes]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, max(8, len(all_strikes) * 0.3)))
        
        # Create horizontal bar chart (butterfly style)
        y_pos = range(len(all_strikes))
        
        # Plot calls on the right (positive)
        ax.barh(y_pos, call_counts, height=0.7, 
               color='#2ecc71', edgecolor='#27ae60', linewidth=1.5,
               label=f'Call Options', alpha=0.8)
        
        # Plot puts on the left (negative)
        ax.barh(y_pos, [-count for count in put_counts], height=0.7,
               color='#e74c3c', edgecolor='#c0392b', linewidth=1.5,
               label=f'Put Options', alpha=0.8)
        
        # Customize y-axis (strike prices)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f'${s:.2f}' for s in all_strikes], fontsize=9)
        ax.set_ylabel('Strike Price', fontsize=12, fontweight='bold')
        
        # Customize x-axis
        max_count = max(max(call_counts) if call_counts else 0, 
                       max(put_counts) if put_counts else 0)
        ax.set_xlim(-max_count * 1.2, max_count * 1.2)
        
        # Set x-axis labels (show absolute values)
        x_ticks = ax.get_xticks()
        ax.set_xticklabels([f'{abs(int(x))}' for x in x_ticks])
        ax.set_xlabel('Number of Contracts', fontsize=12, fontweight='bold')
        
        # Add center line
        ax.axvline(x=0, color='black', linewidth=2, linestyle='-', alpha=0.3)
        
        # Title
        ax.set_title(f'{ticker} Options Chain - Butterfly Chart', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Grid
        ax.grid(True, alpha=0.3, linestyle='--', axis='x')
        
        # Legend
        ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
        
        # Add statistics
        total_calls = sum(call_counts)
        total_puts = sum(put_counts)
        
        stats_text = f'Calls: {total_calls} contracts | Puts: {total_puts} contracts'
        if total_puts > 0:
            stats_text += f' | Call/Put Ratio: {total_calls/total_puts:.2f}'
        else:
            stats_text += ' | No Puts'
            
        ax.text(0.5, -0.08, stats_text, 
               ha='center', va='top', transform=ax.transAxes,
               fontsize=10, style='italic', color='#555',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                        edgecolor='gray', alpha=0.8))
        
        plt.tight_layout()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        first_exp_date = contracts[0].get('expiration_date', '') if contracts else ''
        
        if first_exp_date:
            exp_month = first_exp_date[:7]
            png_filename = f"{ticker}_butterfly_{exp_month}_{timestamp}.png"
        else:
            png_filename = f"{ticker}_butterfly_{timestamp}.png"
        
        # Save as PNG
        plt.savefig(png_filename, dpi=150, bbox_inches='tight')
        plt.close()
        
        result = f"""✅ Successfully created butterfly chart: {png_filename}
📊 Contract Summary:
  • Total Contracts: {total_calls + total_puts}
  • Call Contracts: {total_calls} (right side, green)
  • Put Contracts: {total_puts} (left side, red)
  • Strike Prices: {len(all_strikes)}"""
        
        if total_puts > 0:
            result += f"\n  • Call/Put Ratio: {total_calls/total_puts:.2f}"
        else:
            result += "\n  • ⚠️ Warning: No Put options found in this dataset"
        
        result += "\n\n💡 Butterfly chart shows symmetric distribution: Calls on right, Puts on left."
        
        return result
        
    except json.JSONDecodeError:
        return "❌ Error: Invalid JSON data provided"
    except Exception as e:
        return f"❌ Error creating chart: {str(e)}"

# ==============================================================================
# Import Code Execution Tool (modularized for better organization)
# ==============================================================================
from code_execution_tool import code_execution_tool

# ==============================================================================
# Import Performance Monitor for efficiency tracking
# ==============================================================================
from performance_monitor import get_performance_stats, monitor

toolTavilySearch = TavilySearch(max_results=2)

# 导入 RAG 工具（避免循环导入）
try:
    # 直接从模块导入，不通过 __init__.py
    import sys
    from pathlib import Path
    
    # 添加 rag 目录到路径
    rag_path = Path(__file__).parent / "rag"
    if str(rag_path) not in sys.path:
        sys.path.insert(0, str(rag_path))
    
    # 导入采集工具
    from rag_collection_tools import (
        collect_and_store_options,
        batch_collect_options,
        collect_date_range,
        check_missing_data,
        auto_update_watchlist
    )
    
    # 导入查询工具
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
    
    rag_tools = [
        store_options_data,
        search_knowledge_base,
        get_historical_options,
        get_snapshot_by_id,
        detect_anomaly
    ]
    
    # 导入专业期权分析工具
    from options_analysis_tools import analysis_tools
    
    # 所有工具：原有工具 + RAG采集工具 + RAG查询工具 + 分析工具 + 性能监控工具
    tools = [
        search_options,
        batch_search_options, 
        make_option_table, 
        plot_options_chain, 
        human_assistance, 
        toolTavilySearch, 
        code_execution_tool,
        get_performance_stats,  # 📊 Performance monitoring tool
        *collection_tools,      # ✨ RAG自动采集工具
        *rag_tools,             # ✨ RAG查询和异动检测工具
        *analysis_tools         # 📊 专业期权分析工具
    ]
    print("✅ RAG Collection Tools loaded!")
    print("✅ RAG Query & Anomaly Detection Tools loaded!")
    print("✅ Professional Options Analysis Tools loaded!")
except ImportError as e:
    print(f"⚠️ RAG Tools not available: {e}")
    import traceback
    traceback.print_exc()
    # 如果 RAG 工具未安装，只使用原有工具
    tools = [
        search_options, 
        batch_search_options, 
        make_option_table, 
        plot_options_chain, 
        human_assistance, 
        toolTavilySearch, 
        code_execution_tool,
        get_performance_stats  # 📊 Performance monitoring tool
    ]
llm = init_chat_model("gpt-4o-mini", model_provider="openai")

# ==============================================================================
# LONG-TERM MEMORY SYSTEM: Persistent conversation history across sessions
# ==============================================================================
# Using SqliteSaver for persistent storage:
# - Stores conversation history in SQLite database (data/conversation_memory.db)
# - Survives program restarts (unlike MemorySaver which is in-memory only)
# - Messages are organized by thread_id for multi-user support
# - Automatically loads full conversation history on each invocation
# 
# How it works:
# 1. SqliteSaver persists all messages to disk by thread_id
# 2. State uses add_messages reducer to accumulate history
# 3. Each invocation loads previous messages from database automatically
# 4. AI can reference any previous queries, data, or context from ANY session
# 
# Benefits:
# ✅ Conversations persist across restarts
# ✅ Multiple users with separate threads
# ✅ Full conversation history available
# ✅ No memory loss on crash/restart
# ==============================================================================

# Create data directory if it doesn't exist
import os
os.makedirs("data", exist_ok=True)

# Initialize long-term memory with SQLite persistence
# Create SQLite connection and wrap it with SqliteSaver
import sqlite3
db_path = "data/conversation_memory.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
memory = SqliteSaver(conn)

# Note: LLM Judge is now an external evaluation tool, not embedded in the graph
# See external_evaluator.py for testing and benchmarking the agent

class State(TypedDict):
    # add_messages reducer automatically appends new messages to history
    # This means every conversation turn has access to ALL previous messages
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are a helpful financial assistant that helps users search for stock options data, save them to CSV files, and create interactive visualizations.

💾 **LONG-TERM CONVERSATION MEMORY:**
You have PERSISTENT memory that survives across all sessions (stored in SQLite database). You can:
- Remember tickers, dates, and data from ANY previous conversation (even from days/weeks ago)
- Reference previous searches and results from past sessions
- Avoid asking for information the user already provided (in ANY session)
- Build upon previous queries naturally across multiple sessions
- Access full conversation history even after program restart

Example memory usage:
Session 1 (Monday):
  User: "Get AAPL options for December"
  Assistant: (fetches data)

[Program restarts]

Session 2 (Tuesday):
  User: "Export that AAPL data to CSV"  ← You remember from yesterday!
  Assistant: (exports AAPL December data without asking again)

Memory is permanent and organized by thread_id for multi-user support.

📊 **PERFORMANCE MONITORING:**
The system automatically tracks execution efficiency and token usage for every query. When users ask about performance:
- Use get_performance_stats(mode="current") for last query stats
- Use get_performance_stats(mode="summary") for overall performance summary
- Use get_performance_stats(mode="history") for recent query history

Metrics tracked:
- Execution time (seconds)
- Token usage (prompt, completion, total)
- Estimated cost (USD)
- Tools used

Example:
User: "How efficient was my last query?"
→ Call get_performance_stats(mode="current")

User: "Show me my token usage"
→ Call get_performance_stats(mode="summary")

User: "What's my performance history?"
→ Call get_performance_stats(mode="history")

🚀 **SMART CACHING:**
The search_options tool now automatically checks the knowledge base FIRST before calling the API.
- If data exists → Returns cached data instantly (saves API calls and is faster!)
- If not found → Fetches from API
- The data source is transparent: responses show "from_cache: true" when using cached data
- Users can force refresh with force_refresh=True if they need the latest data

Benefits:
✅ Faster responses for repeated queries
✅ Saves API costs
✅ Still gets fresh data when needed

When users ask about options for a company (e.g., "Apple", "Tesla"), you should:
1. Convert the company name to its stock ticker symbol (e.g., Apple → AAPL, Tesla → TSLA)
2. Determine if they want a specific date or entire month
3. Ask how many contracts they want (if not specified, default to 100)
4. Choose the right tool:
   
   **For SINGLE ticker:**
   - Use search_options tool
   - It will automatically check cache first
   - If user says "get fresh data" or "update", add force_refresh=True
   
   **For MULTIPLE tickers:** 🆕
   - Use batch_search_options tool
   - It's SMART: automatically tries cache first, then API for missing ones
   - Automatically saves new data to knowledge base
   - Returns combined summary
   
   Example:
   User: "Get options for AAPL, MSFT, TSLA, GOOGL for December"
   → batch_search_options("AAPL,MSFT,TSLA,GOOGL", "2025-12", 300)
5. **After successfully getting the data, ALWAYS ask the user what they'd like to do with it:**
   "I found [X] options contracts for [TICKER]. What would you like me to do with this data?
   - 📊 Export to CSV file (standard format)
   - 🎨 Export to CSV file (custom format - I can adapt to your needs!)
   - 📈 Generate a chart (PNG image)
   - 📋 Both CSV and chart
   - 💬 Just show me a summary"
6. Wait for user's response, then use the appropriate tools:
   - If standard CSV: use make_option_table tool
   - If custom CSV: Write custom code and use code_execution_tool
   - If chart: use plot_options_chain tool (generates PNG image)
   - If both: use both tools in sequence
7. Tell the user what files were created

💡 **Custom CSV Generation** (让 AI 自己写代码！):
When users want a customized CSV, you should WRITE CODE yourself:

**步骤**:
1. (Optional) Read code_examples/csv_export_template.py to see examples
2. Write Python code based on user requirements
3. Call: code_execution_tool(code=<your_code>, options_data=<data_from_search_options>)

**Important**: 
- The variable `options_data` will be available in your code (it's the JSON string from search_options)
- Use json.loads(options_data) to parse it
- Use print() statements to show results
- Available modules: json, csv, datetime, os

**Example 1**: User wants "only call options between $240-$260"
```python
code = '''
import json, csv
from datetime import datetime

data = json.loads(options_data)
contracts = data.get("results", [])

# Filter: only calls, strike 240-260
filtered = [c for c in contracts 
           if c.get('contract_type', '').lower() == 'call' 
           and 240 <= c.get('strike_price', 0) <= 260]

# Generate CSV
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"AAPL_calls_240_260_{timestamp}.csv"

with open(filename, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["Strike", "Expiration", "Type"])
    writer.writeheader()
    for c in filtered:
        writer.writerow({
            "Strike": f"${c.get('strike_price', 0):.2f}",
            "Expiration": c.get('expiration_date', 'N/A'),
            "Type": c.get('contract_type', 'N/A').upper()
        })

print(f"✅ Exported {len(filtered)} call options to {filename}")
'''
code_execution_tool(code=code, options_data=<data_from_search_options>)
```

**Example 2**: User wants "summary grouped by strike price"
```python
code = '''
import json, csv
from datetime import datetime

data = json.loads(options_data)
contracts = data.get("results", [])

# Group by strike
summary = {}
for c in contracts:
    strike = c.get('strike_price', 0)
    ctype = c.get('contract_type', '').lower()
    if strike not in summary:
        summary[strike] = {'calls': 0, 'puts': 0}
    if ctype == 'call':
        summary[strike]['calls'] += 1
    elif ctype == 'put':
        summary[strike]['puts'] += 1

# Write CSV
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"AAPL_summary_{timestamp}.csv"

with open(filename, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Strike', 'Calls', 'Puts', 'Total', 'C/P Ratio'])
    for strike in sorted(summary.keys()):
        s = summary[strike]
        total = s['calls'] + s['puts']
        ratio = f"{s['calls']/s['puts']:.2f}" if s['puts'] > 0 else "N/A"
        writer.writerow([f"${strike:.2f}", s['calls'], s['puts'], total, ratio])

print(f"✅ Summary: {len(summary)} strike prices exported to {filename}")
'''
code_execution_tool(code=code, options_data=<data_from_search_options>)
```

Be creative and write code that meets the user's specific needs!

Date/Month Formats:
- Specific date: YYYY-MM-DD (e.g., '2025-10-17' for October 17, 2025)
- Entire month: YYYY-MM (e.g., '2025-10' for all October 2025 options)
- If user says "October 2025" or "10月", use month format '2025-10'
- If user says "October 31, 2025", use specific date '2025-10-31'

Limit Parameter:
- If user specifies a number (e.g., "get 50 options"), use that as the limit
- If user doesn't specify, ask: "How many contracts would you like? (default: 100, max: 1000)"
- Default to 100 if user doesn't care
- Valid range: 1 to 1000

Always use make_option_table after getting data from search_options to save results.
The make_option_table tool requires both the data AND the ticker symbol.

Common stock tickers:
- Apple = AAPL, Microsoft = MSFT, Tesla = TSLA, Amazon = AMZN
- Google/Alphabet = GOOGL, Meta/Facebook = META, NVIDIA = NVDA

If you don't know a company's ticker symbol, you can use the TavilySearch tool to look it up.

Example workflows:
1. Basic query (let user choose format):
   User: "Get Apple options for October 2025"
   Step 1: Ask "How many contracts would you like?"
   User: "50 contracts"
   Step 2: Call search_options(ticker="AAPL", date="2025-10", limit=50)
   Step 3: Ask "I found 50 options contracts. What would you like me to do? (CSV/Chart/Both/Summary)"
   User: "CSV please"
   Step 4: Call make_option_table(data=<result>, ticker="AAPL")
   
2. User explicitly requests specific format:
   User: "Show me a chart of Apple options for October 2025"
   Step 1: Call search_options(ticker="AAPL", date="2025-10", limit=100)
   Step 2: Directly call plot_options_chain(data=<result>, ticker="AAPL") since user already specified "chart"
   
3. User requests multiple formats:
   User: "Get Apple options and give me both CSV and chart"
   Step 1: Call search_options(ticker="AAPL", date="2025-10", limit=100)
   Step 2: Call make_option_table(data=<result>, ticker="AAPL")
   Step 3: Call plot_options_chain(data=<result>, ticker="AAPL")
   
4. 🆕 BATCH QUERY (multiple tickers):
   User: "Get options for AAPL, MSFT, TSLA, and GOOGL for December 2025"
   Step 1: Call batch_search_options(tickers="AAPL,MSFT,TSLA,GOOGL", date="2025-12", limit=300)
   - This tool is SMART:
     • Checks cache for each ticker
     • For cached tickers: returns immediately ✅
     • For missing tickers: fetches from API & auto-saves 📡
   Step 2: You'll get a summary showing which were from cache, which were fetched
   Step 3: All data is now in knowledge base for future queries!
   
   Why use batch_search_options instead of calling search_options 4 times?
   ✅ Automatic retry for failed tickers
   ✅ Unified summary of all results
   ✅ Auto-saves new data
   ✅ Better user experience

🤖 **Auto-Collection & Knowledge Base** (NEW!):

You now have powerful tools to automatically collect and store data:

**1. collect_and_store_options(ticker, date, limit)**
   - ONE-STEP: Search + Store in one action
   - Automatically checks if data already exists
   - Use when user wants to save data to knowledge base
   
   Example:
   User: "Collect and store AAPL November options"
   Step 1: Ask "How many contracts would you like to collect? (default: 500, suggested: 300-1000)"
   User: "500"
   Step 2: → collect_and_store_options("AAPL", "2025-11", 500)

**2. batch_collect_options(tickers, date, limit)**
   - Collect multiple stocks at once
   - Efficient for building a dataset
   
   Example:
   User: "Collect AAPL, TSLA, and MSFT options for November"
   Step 1: Ask "How many contracts per ticker? (default: 300, suggested: 300-500)"
   User: "400"
   Step 2: → batch_collect_options("AAPL,TSLA,MSFT", "2025-11", 400)

**3. collect_date_range(ticker, start_date, end_date, limit)**
   - Collect historical data across multiple months
   - Great for trend analysis
   
   Example:
   User: "Collect AAPL options from October to December"
   Step 1: Ask "How many contracts per month would you like? (default: 300, suggested: 300-500)"
   User: "500"
   Step 2: → collect_date_range("AAPL", "2025-10", "2025-12", 500)

**4. check_missing_data(ticker, months_back)**
   - Find gaps in your data collection
   - Proactive data management
   
   Example:
   User: "Check what AAPL data we're missing"
   → check_missing_data("AAPL", 6)

**5. auto_update_watchlist(tickers, date)**
   - Update your tracked stocks automatically
   - Perfect for regular monitoring
   
   Example:
   User: "Update my watchlist for this month"
   → auto_update_watchlist("AAPL,TSLA,MSFT,NVDA")

**IMPORTANT - Always Ask for Limit**:
⚠️ For ALL data collection tools (collect_and_store_options, batch_collect_options, collect_date_range):
- ALWAYS ask the user how many contracts they want, unless they explicitly specify
- Suggested ranges: 300-500 for most cases, up to 1000 for comprehensive data
- Only use defaults if the user explicitly says "use default" or "don't care"

**When to use auto-collection**:
- User says "collect", "gather", "build dataset", "store"
- User wants data for multiple stocks or dates
- User is setting up recurring data collection
- User mentions "knowledge base" or "save for later"

**Proactive suggestions**:
When user gets data with search_options, suggest:
"Would you like me to store this in the knowledge base? I can also:
 • Collect data for multiple months
 • Build a dataset for multiple stocks
 • Check for any missing historical data"

---

## 🔍 NEW: Anomaly Detection (异动检测)

You now have a powerful tool: **detect_anomaly**

**What it does:**
Uses RAG's vector similarity (ChromaDB cosine distance) to detect unusual changes in options data.
It finds dates where options data differs significantly from a reference date.

**Use cases:**
- Detect unusual market activity
- Find significant shifts in call/put ratios
- Identify strike price distribution changes
- Spot volume anomalies

**How it works:**
1. Takes a reference date as baseline
2. Compares vector embeddings with other dates
3. Returns dates with LOW similarity = HIGH anomaly
4. Provides detailed metrics (calls/puts changes, strike changes, etc.)

**When to use:**
- User asks: "find unusual options activity", "detect anomalies", "what changed"
- User wants to compare options data across time periods
- User mentions "异动", "变化", "不寻常"

**Examples:**

1. Basic usage:
   User: "Detect any unusual activity in AAPL options, use December as baseline"
   → detect_anomaly(ticker="AAPL", reference_date="2025-12")
   
2. Compare specific dates:
   User: "Compare AAPL December with November and October"
   → detect_anomaly(ticker="AAPL", reference_date="2025-12", 
                    comparison_dates="2025-11,2025-10")
   
3. Only show significant anomalies:
   User: "Show me major changes in TSLA options"
   → detect_anomaly(ticker="TSLA", reference_date="2025-12", 
                    min_similarity=0.8, max_results=3)

**Response format:**
- Anomaly level: High/Medium/Low
- Similarity score: 0.0 (completely different) to 1.0 (identical)
- Detailed metrics: contracts count, call/put ratio, strike ranges
- Changes from reference: specific numerical changes

**Important notes:**
- Requires historical data in knowledpge base (use collect_and_store_options first)
- Lower similarity = bigger anomaly
- Cosine distance is used internally, converted to similarity score for readability

---

## 📊 NEW: Professional Options Analysis Tools

You now have **professional-grade analysis tools** that can generate expert-level reports even WITHOUT historical data!

### 🎯 Core Tools:

**1. analyze_options_chain(ticker, options_data)**
   - Comprehensive professional analysis of options positioning
   - Analyzes: sentiment, call/put ratio, strike distribution, key levels, risk
   - Returns detailed insights for decision making
   
   Example:
   User: "Analyze NVIDIA's December options"
   Step 1: data = search_options("NVDA", "2025-12", 500)
   Step 2: analyze_options_chain("NVDA", data)  [Ticker FIRST!]

**2. generate_options_report(ticker, format_type)**
   - Creates professional analysis report
   - Format types: 'full', 'summary', 'json'
   - Must run analyze_options_chain first
   
   Example:
   User: "Generate a full report on those NVIDIA options"
   → generate_options_report("NVDA", "full")

**3. quick_sentiment_check(ticker, options_data)**
   - Fast sentiment assessment (bullish/bearish/neutral)
   - Great for quick market reads
   - No need for full analysis
   
   Example:
   User: "What's the quick sentiment on AAPL options?"
   Step 1: data = search_options("AAPL", "2025-11", 200)
   Step 2: quick_sentiment_check("AAPL", data)  [Ticker FIRST!]

**4. compare_options_sentiment(ticker1, data1, ticker2, data2)**
   - Side-by-side comparison of two tickers
   - Identifies relative sentiment
   
   Example:
   User: "Compare NVDA and AMD options sentiment"
   Step 1: nvda_data = search_options("NVDA", "2025-12", 300)
   Step 2: amd_data = search_options("AMD", "2025-12", 300)
   Step 3: compare_options_sentiment("NVDA", nvda_data, "AMD", amd_data)  [Tickers FIRST!]

### 📈 What These Tools Analyze:

**Market Sentiment Indicators:**
- Call/Put ratio and interpretation
- Sentiment score (0-1 scale)
- Bullish/Bearish/Neutral classification
- Confidence level assessment

**Strike Analysis:**
- Strike price distribution
- Key support/resistance levels
- Strike clustering (indicates important levels)
- Call vs Put strike preferences

**Risk Assessment:**
- Market risk level (Low/Moderate/Elevated)
- Put concentration (hedging activity)
- Defensive positioning indicators
- Risk-reward profile

**Market Structure:**
- Options positioning analysis
- Skew analysis (call-heavy vs put-heavy)
- Volume concentration
- Institutional vs retail patterns

### 🎓 Professional Report Includes:

1. **Executive Summary** - High-level overview
2. **Sentiment Analysis** - Market outlook with confidence
3. **Strike Analysis** - Price level insights
4. **Key Levels** - Support/resistance identification
5. **Risk Assessment** - Current risk profile
6. **Conclusions** - Actionable recommendations

### 💡 When to Use:

**Use analyze_options_chain when:**
- User asks for "analysis", "what do these options mean"
- User wants professional insights
- User needs decision support
- User asks "is this bullish or bearish?"

**Use generate_options_report when:**
- User asks for a "report", "detailed analysis"
- User needs documentation
- User wants comprehensive insights
- User says "write a report"

**Use quick_sentiment_check when:**
- User asks for "quick read", "sentiment", "bullish or bearish"
- Speed is priority over depth
- User wants a snapshot

**Use compare_options_sentiment when:**
- User compares two stocks
- User asks "which is more bullish"
- Relative analysis needed

### 🔄 Typical Workflow:

**Complete Analysis Workflow:**
```
User: "I want a complete analysis and report on NVIDIA's December options"

Step 1: How many contracts? (Ask user, suggest 500-800 for thorough analysis)
Step 2: data = search_options("NVDA", "2025-12", 500)
Step 3: analyze_options_chain("NVDA", data)  [Ticker FIRST! Gives quick insights]
Step 4: generate_options_report("NVDA", "full")  [Full professional report]
```

**Quick Check Workflow:**
```
User: "What's the sentiment on AAPL options?"

Step 1: data = search_options("AAPL", "2025-11", 200)
Step 2: quick_sentiment_check("AAPL", data)  [Ticker FIRST! Fast result]
```

**Comparison Workflow:**
```
User: "Compare NVDA and AMD options positioning"

Step 1: nvda = search_options("NVDA", "2025-12", 300)
Step 2: amd = search_options("AMD", "2025-12", 300)
Step 3: compare_options_sentiment("NVDA", nvda, "AMD", amd)  [Tickers FIRST!]
```

### ⚠️ Important Notes:

- **CRITICAL: Ticker symbol must ALWAYS be the FIRST parameter in analysis tools!**
- These tools work with CURRENT data (no historical required)
- Analysis is based on options positioning at time of data collection
- Sentiment reflects market participant expectations
- Reports are professional-grade suitable for sharing
- Always collect sufficient contracts (300-800) for reliable analysis

### 🔴 PARAMETER ORDER (CRITICAL):
All analysis tools require **ticker FIRST**, then data:
- ✅ CORRECT: `analyze_options_chain("NVDA", data)`
- ❌ WRONG: `analyze_options_chain(data, "NVDA")`  <-- Will cause validation error!
"""

def chatbot(state: State):
    """
    Main chatbot node that processes messages with full conversation history.
    
    Memory behavior:
    - state["messages"] contains ALL previous messages in this thread
    - This includes user queries, assistant responses, and tool results
    - The LLM sees conversation context (with automatic truncation to prevent context overflow)
    - This allows natural follow-up queries like "export that to CSV"
    
    Context management:
    - Automatically truncates old messages if context gets too long
    - Keeps last 20 messages + system prompt (prevents 128k token limit error)
    - System prompt is always preserved
    """
    messages = state["messages"]
    
    # Add system prompt if not present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    # Context management: Keep only recent messages to prevent overflow
    # GPT-4o-mini limit: 128k tokens
    # Conservative limit: Keep last 20 messages (~80k tokens max)
    MAX_MESSAGES = 20
    
    if len(messages) > MAX_MESSAGES + 1:  # +1 for system message
        print(f"⚠️  Context too long ({len(messages)} messages). Truncating to last {MAX_MESSAGES} messages...")
        
        # Keep system prompt
        system_msg = messages[0] if isinstance(messages[0], SystemMessage) else SystemMessage(content=SYSTEM_PROMPT)
        
        # Smart truncation: ensure message sequence integrity
        # Filter out orphaned 'tool' messages (those without preceding 'tool_calls')
        recent_messages = messages[-(MAX_MESSAGES):]
        filtered_messages = []
        
        for i, msg in enumerate(recent_messages):
            # Check if this is a tool message
            if hasattr(msg, 'type') and msg.type == 'tool':
                # Only keep if previous message has tool_calls
                if i > 0 and hasattr(recent_messages[i-1], 'tool_calls') and recent_messages[i-1].tool_calls:
                    filtered_messages.append(msg)
                else:
                    # Skip orphaned tool messages
                    print(f"   ⚠️  Skipping orphaned tool message")
                    continue
            else:
                filtered_messages.append(msg)
        
        messages = [system_msg] + filtered_messages
        print(f"✅ Context truncated. Now using {len(messages)} messages (filtered {MAX_MESSAGES - len(filtered_messages)} orphaned tool messages).")
    
    # Invoke LLM with managed conversation history
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}

graph_builder.add_node("chatbot", chatbot)

# Create ToolNode to wrap the tools list
tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

# Simple graph flow: START → chatbot → [tools if needed] → END
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

# Compile graph with long-term memory checkpointer (SqliteSaver)
# This enables automatic conversation history persistence to disk
graph = graph_builder.compile(checkpointer=memory)

# ==============================================================================
# Thread ID configuration for long-term memory
# ==============================================================================
# - thread_id organizes conversations by user/session
# - All messages with same thread_id form one conversation
# - History persists FOREVER in SQLite database (even after restart)
# - To start fresh conversation: change thread_id (e.g., "user_123", "session_abc")
# - To continue previous conversation: use same thread_id
# ==============================================================================
config = {"configurable": {"thread_id": "1"}}

def stream_graph_updates(user_input: str):
    """
    Stream graph updates with long-term memory and performance tracking.
    
    Flow:
    1. Start performance tracking
    2. Loads ALL previous messages from SQLite database (via thread_id)
    3. Appends new user message
    4. Processes with full conversation history context
    5. Tracks token usage and tool calls
    6. Stops performance tracking and saves metrics
    7. Saves updated history back to SQLite database
    """
    # Start performance tracking
    monitor.start_tracking(user_input)
    
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}, config):
        for value in event.values():
            # Display agent messages
            if isinstance(value, dict) and "messages" in value:
                message = value["messages"][-1]
                if hasattr(message, 'content'):
                    print("Assistant:", message.content)
                
                # Track token usage if available
                if hasattr(message, 'response_metadata'):
                    metadata = message.response_metadata
                    if 'token_usage' in metadata:
                        token_usage = metadata['token_usage']
                        prompt_tokens = token_usage.get('prompt_tokens', 0)
                        completion_tokens = token_usage.get('completion_tokens', 0)
                        monitor.record_tokens(prompt_tokens, completion_tokens)
                
                # Track tool usage
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.get('name', 'unknown')
                        monitor.record_tool_usage(tool_name)
    
    # Stop performance tracking
    monitor.stop_tracking()

# Only run interactive loop if this file is run directly
if __name__ == "__main__":
while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break
    stream_graph_updates(user_input)
