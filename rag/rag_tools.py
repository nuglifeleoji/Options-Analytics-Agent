"""
RAG Tools for LangChain Integration
定义可以被 Agent 使用的 RAG 工具

Enhanced with LLM-powered summarization for better retrieval results.
"""
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model

# 导入核心功能
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from rag_knowledge_base import (
    generate_embedding,
    create_document_text,
    extract_metadata,
    store_to_chromadb,
    store_to_sqlite,
    search_chromadb,
    query_sqlite,
    get_from_sqlite
)

# ==============================================================================
# LLM Summarizer for Enhanced RAG
# ==============================================================================
# Initialize LLM for post-retrieval summarization
_summarizer_llm = None

def get_summarizer_llm():
    """Get or initialize the LLM for summarization."""
    global _summarizer_llm
    if _summarizer_llm is None:
        _summarizer_llm = init_chat_model("gpt-4o-mini", model_provider="openai")
    return _summarizer_llm


def summarize_retrieval_results(raw_data: str, query_context: str, result_type: str = "general") -> str:
    """
    Use LLM to summarize and organize retrieval results.
    
    Args:
        raw_data: Raw retrieval results (formatted text or JSON)
        query_context: Original user query for context
        result_type: Type of results ("search", "historical", "snapshot", "anomaly")
    
    Returns:
        LLM-generated summary in natural language
    """
    try:
        llm = get_summarizer_llm()
        
        # Build summarization prompt based on result type
        if result_type == "search":
            system_prompt = """You are an expert financial data analyst. Your task is to summarize semantic search results from an options database.

Given the raw search results below, provide a clear, concise summary that:
1. Highlights the most relevant findings
2. Organizes information by ticker and date
3. Points out key metrics (total contracts, call/put ratios, strike ranges)
4. Notes similarity scores and relevance
5. Provides actionable insights

Keep the summary professional, concise, and easy to understand."""

        elif result_type == "historical":
            system_prompt = """You are an expert financial data analyst. Your task is to summarize historical options data.

Given the raw historical data below, provide a clear summary that:
1. Shows trends over time (if multiple snapshots)
2. Highlights significant changes in call/put ratios, volume, or strike ranges
3. Organizes data chronologically
4. Points out any notable patterns or anomalies
5. Provides context for the data

Keep the summary professional and data-focused."""

        elif result_type == "snapshot":
            system_prompt = """You are an expert financial data analyst. Your task is to summarize a specific options snapshot.

Given the raw snapshot data below, provide a clear summary that:
1. Gives an overview of the options chain
2. Highlights key statistics (total contracts, call/put split, strike distribution)
3. Points out any notable characteristics
4. Presents data in an easy-to-understand format
5. Provides relevant context

Keep the summary professional and detailed where appropriate."""

        elif result_type == "anomaly":
            system_prompt = """You are an expert financial data analyst. Your task is to summarize anomaly detection results.

Given the raw anomaly data below, provide a clear summary that:
1. Explains what anomalies were detected
2. Highlights the significance of each anomaly (similarity scores, changes)
3. Compares metrics between reference and anomalous data
4. Provides possible interpretations
5. Suggests follow-up actions

Keep the summary professional and focused on actionable insights."""

        else:
            system_prompt = """You are an expert financial data analyst. Summarize the following data clearly and concisely, 
highlighting key insights and organizing information in an easy-to-understand format."""
        
        user_prompt = f"""User Query: "{query_context}"

Raw Retrieved Data:
{raw_data}

Please provide a clear, organized summary of these results."""
        
        # Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = llm.invoke(messages)
        summary = response.content
        
        return summary
        
    except Exception as e:
        # If summarization fails, return original data
        print(f"⚠️  Summarization failed: {e}")
        return raw_data


@tool
def store_options_data(data: str, ticker: str, date: str) -> str:
    """Store options data to the RAG knowledge base.
    
    This tool stores options data for future retrieval and analysis.
    The data will be stored in both a vector database (for semantic search)
    and a relational database (for structured queries).
    
    Args:
        data: JSON string containing options data from search_options tool
        ticker: Stock ticker symbol (e.g., 'AAPL')
        date: Date or month of the options data (e.g., '2025-11' or '2025-11-07')
    
    Returns:
        Confirmation message with storage details
    
    Example:
        data = search_options("AAPL", "2025-11", 500)
        result = store_options_data(data, "AAPL", "2025-11")
    """
    try:
        # 解析数据
        options_data = json.loads(data)
        
        if "results" not in options_data:
            return "❌ Error: Invalid options data format"
        
        contracts = options_data.get("results", [])
        if not contracts:
            return "❌ Error: No contracts found in data"
        
        # 生成唯一ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snap_{ticker}_{date}_{timestamp}"
        
        # 提取元数据
        metadata = extract_metadata(options_data, ticker, date)
        
        # 创建文本描述
        doc_text = create_document_text(options_data, ticker, date)
        
        # 生成 embedding
        print(f"🔄 Generating embedding for {ticker} {date}...")
        embedding = generate_embedding(doc_text)
        
        # 存储到 ChromaDB
        print(f"💾 Storing to vector database...")
        chroma_success = store_to_chromadb(
            snapshot_id=snapshot_id,
            text=doc_text,
            embedding=embedding,
            metadata=metadata
        )
        
        # 存储到 SQLite
        print(f"💾 Storing to relational database...")
        sqlite_success = store_to_sqlite(
            snapshot_id=snapshot_id,
            ticker=ticker,
            date=date,
            options_data=options_data,
            metadata=metadata
        )
        
        if chroma_success and sqlite_success:
            result = f"""✅ Options data stored successfully!

📊 Storage Details:
  • Snapshot ID: {snapshot_id}
  • Ticker: {ticker}
  • Date: {date}
  • Total Contracts: {metadata['total_contracts']}
  • Call Options: {metadata['calls_count']}
  • Put Options: {metadata['puts_count']}
  • Strike Range: ${metadata['strike_min']:.2f} - ${metadata['strike_max']:.2f}
  • Timestamp: {metadata['timestamp']}

💾 Stored in:
  • Vector Database (ChromaDB): ✅ Semantic search enabled
  • Relational Database (SQLite): ✅ Structured queries enabled

🔍 You can now retrieve this data using:
  • search_knowledge_base() - semantic search
  • get_historical_options() - date range queries
"""
            return result
        else:
            return "❌ Error: Failed to store data in one or both databases"
            
    except json.JSONDecodeError:
        return "❌ Error: Invalid JSON data provided"
    except Exception as e:
        return f"❌ Error storing data: {str(e)}"


@tool
def search_knowledge_base(
    query: str,
    ticker: str = None,
    limit: int = 5
) -> str:
    """Semantic search in the options knowledge base using natural language.
    
    This tool uses AI-powered semantic search to find relevant historical
    options data based on natural language queries.
    
    Args:
        query: Natural language query (e.g., "AAPL options with high call/put ratio")
        ticker: (Optional) Filter results by specific ticker
        limit: Number of results to return (default: 5, max: 20)
    
    Returns:
        Formatted search results with relevant options data
    
    Example:
        search_knowledge_base("Show me Apple options from November with high volatility")
        search_knowledge_base("Find options similar to current TSLA", ticker="TSLA", limit=3)
    """
    try:
        # 限制最大返回数量
        limit = min(limit, 20)
        
        # 构建 where 条件
        where = {}
        if ticker:
            where["ticker"] = ticker
        
        # 搜索
        print(f"🔍 Searching knowledge base: '{query}'...")
        results = search_chromadb(
            query_text=query,
            limit=limit,
            where=where if where else None
        )
        
        if not results:
            return f"🔍 No results found for query: '{query}'"
        
        # 格式化结果
        output = f"🔍 Found {len(results)} relevant snapshots:\n\n"
        
        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            similarity = result['similarity']
            
            # 只显示相似度足够高的结果
            if similarity < 0.7:
                continue
            
            output += f"**{i}. {metadata['ticker']} - {metadata['date']}** (Similarity: {similarity:.2%})\n"
            output += f"   • Snapshot ID: {result['id']}\n"
            output += f"   • Total Contracts: {metadata['total_contracts']}\n"
            output += f"   • Calls: {metadata['calls_count']} | Puts: {metadata['puts_count']}\n"
            output += f"   • Strike Range: ${metadata['strike_min']:.2f} - ${metadata['strike_max']:.2f}\n"
            output += f"   • Captured: {metadata['timestamp']}\n\n"
        
        output += "💡 To retrieve full data, use: get_snapshot_by_id(snapshot_id)"
        
        # ===== LLM Summarization =====
        print(f"🤖 Summarizing results with LLM...")
        summary = summarize_retrieval_results(output, query, result_type="search")
        
        return summary
        
    except Exception as e:
        return f"❌ Error searching knowledge base: {str(e)}"


@tool
def get_historical_options(
    ticker: str,
    start_date: str = None,
    end_date: str = None,
    limit: int = 10
) -> str:
    """Get historical options data for a specific ticker and date range.
    
    This tool performs structured queries on the knowledge base to retrieve
    historical options data.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        limit: Maximum number of snapshots to return (default: 10)
    
    Returns:
        Historical options data with statistics
    
    Example:
        get_historical_options("AAPL", "2025-10-01", "2025-10-31")
        get_historical_options("TSLA", limit=5)  # Get latest 5 snapshots
    """
    try:
        print(f"📊 Querying historical data for {ticker}...")
        
        results = query_sqlite(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        if not results:
            date_range = f" from {start_date} to {end_date}" if start_date and end_date else ""
            return f"📊 No historical data found for {ticker}{date_range}"
        
        # 格式化结果
        output = f"📊 Historical Options Data for {ticker}\n"
        if start_date and end_date:
            output += f"Date Range: {start_date} to {end_date}\n"
        output += f"Found {len(results)} snapshots:\n\n"
        
        for i, result in enumerate(results, 1):
            output += f"**{i}. {result['date']}**\n"
            output += f"   • Snapshot ID: {result['id']}\n"
            output += f"   • Total Contracts: {result['total_contracts']}\n"
            output += f"   • Calls: {result['calls_count']} | Puts: {result['puts_count']}\n"
            output += f"   • Strike Range: ${result['strike_min']:.2f} - ${result['strike_max']:.2f}\n"
            
            # 计算 Call/Put ratio
            if result['puts_count'] > 0:
                ratio = result['calls_count'] / result['puts_count']
                output += f"   • Call/Put Ratio: {ratio:.2f}\n"
            
            output += f"   • Captured: {result['timestamp']}\n\n"
        
        # ===== LLM Summarization =====
        print(f"🤖 Summarizing historical data with LLM...")
        query_context = f"Historical options data for {ticker}"
        if start_date and end_date:
            query_context += f" from {start_date} to {end_date}"
        summary = summarize_retrieval_results(output, query_context, result_type="historical")
        
        return summary
        
    except Exception as e:
        return f"❌ Error retrieving historical data: {str(e)}"


@tool
def get_snapshot_by_id(snapshot_id: str) -> str:
    """Retrieve complete options data for a specific snapshot ID.
    
    Args:
        snapshot_id: The unique identifier of the snapshot
    
    Returns:
        Complete JSON data for the snapshot
    """
    try:
        result = get_from_sqlite(snapshot_id)
        
        if not result:
            return f"❌ Snapshot not found: {snapshot_id}"
        
        # 返回完整数据（格式化为可读的JSON）
        output = f"📦 Snapshot: {snapshot_id}\n\n"
        output += "📊 Metadata:\n"
        output += json.dumps(result['metadata'], indent=2)
        output += "\n\n💾 Complete Data Available\n"
        output += f"Total contracts: {result['data'].get('count', 0)}\n"
        
        # Add sample data for context
        if result['data'].get('results'):
            output += "\n📋 Sample Contracts (first 5):\n"
            for i, contract in enumerate(result['data']['results'][:5], 1):
                output += f"{i}. {contract.get('details', {}).get('contract_type', 'N/A')} "
                output += f"Strike: ${contract.get('details', {}).get('strike_price', 'N/A')} "
                output += f"Exp: {contract.get('details', {}).get('expiration_date', 'N/A')}\n"
        
        # ===== LLM Summarization =====
        print(f"🤖 Summarizing snapshot with LLM...")
        query_context = f"Detailed snapshot data for {snapshot_id}"
        summary = summarize_retrieval_results(output, query_context, result_type="snapshot")
        
        return summary
        
    except Exception as e:
        return f"❌ Error retrieving snapshot: {str(e)}"


@tool
def detect_anomaly(
    ticker: str,
    reference_date: str,
    comparison_dates: Optional[str] = None,
    min_similarity: float = 0.0,
    max_results: int = 5
) -> str:
    """
    🔍 ANOMALY DETECTION: Detect unusual changes in options data using vector similarity.
    
    This tool uses RAG's vector database (ChromaDB) to find options data that differs
    significantly from a reference date. It's useful for detecting:
    - Unusual market activity
    - Significant shifts in call/put ratios
    - Strike price distribution changes
    - Volume anomalies
    
    How it works:
    1. Takes a reference date as the baseline
    2. Compares it to other dates using vector similarity (cosine distance)
    3. Returns dates with LOW similarity = HIGH anomaly
    
    Args:
        ticker: Stock ticker (e.g., 'AAPL')
        reference_date: Reference date in YYYY-MM or YYYY-MM-DD format (baseline)
        comparison_dates: Optional comma-separated dates to compare (e.g., '2025-11,2025-10')
                         If None, compares against ALL historical data for this ticker
        min_similarity: Minimum similarity threshold (0.0-1.0). Only show results with
                       similarity >= this value. Default 0.0 (show all)
        max_results: Maximum number of anomalies to return (default: 5)
        
    Returns:
        JSON string with detected anomalies, sorted by anomaly level (highest first)
        
    Example 1 - Compare against all history:
        detect_anomaly(ticker="AAPL", reference_date="2025-12")
        
    Example 2 - Compare specific dates:
        detect_anomaly(ticker="AAPL", reference_date="2025-12", 
                      comparison_dates="2025-11,2025-10")
                      
    Example 3 - Only show significant anomalies:
        detect_anomaly(ticker="AAPL", reference_date="2025-12", 
                      min_similarity=0.8)
    """
    try:
        from rag_knowledge_base import detect_options_anomaly
        
        # 解析 comparison_dates
        comparison_list = None
        if comparison_dates:
            comparison_list = [d.strip() for d in comparison_dates.split(',')]
        
        # 调用底层函数
        anomalies = detect_options_anomaly(
            ticker=ticker,
            reference_date=reference_date,
            comparison_dates=comparison_list,
            min_similarity=min_similarity,
            max_results=max_results
        )
        
        # 检查错误
        if anomalies and isinstance(anomalies[0], dict) and "error" in anomalies[0]:
            return json.dumps(anomalies[0], indent=2)
        
        # 格式化结果
        if not anomalies:
            return json.dumps({
                "message": f"No anomalies detected for {ticker} with reference date {reference_date}",
                "suggestion": "Try lowering min_similarity or collecting more historical data"
            }, indent=2)
        
        # 生成报告
        report = {
            "ticker": ticker.upper(),
            "reference_date": reference_date,
            "anomalies_found": len(anomalies),
            "analysis": f"Compared against {'all historical data' if not comparison_list else f'{len(comparison_list)} specific dates'}",
            "anomalies": anomalies
        }
        
        # Convert to formatted string for LLM
        raw_report = json.dumps(report, indent=2)
        
        # ===== LLM Summarization =====
        print(f"🤖 Summarizing anomaly detection with LLM...")
        query_context = f"Anomaly detection for {ticker} using {reference_date} as reference"
        summary = summarize_retrieval_results(raw_report, query_context, result_type="anomaly")
        
        return summary
        
    except ImportError:
        return json.dumps({
            "error": "RAG anomaly detection not available",
            "message": "Make sure rag_knowledge_base is properly configured"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Anomaly detection failed: {str(e)}"
        }, indent=2)


rag_tools = [
    store_options_data,
    search_knowledge_base,
    get_historical_options,
    get_snapshot_by_id,
    detect_anomaly  
]

if __name__ == "__main__":
    print("RAG Tools loaded:")
    for tool in rag_tools:
        print(f"  • {tool.name}")

