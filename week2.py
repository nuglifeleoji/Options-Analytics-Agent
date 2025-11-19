import os
import json
import requests
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from search_tools import search_options, make_option_table, plot_options_chain, human_assistance, toolTavilySearch, code_execution_tool

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

# Initialize LLM
llm = init_chat_model("gpt-4o-mini", model_provider="openai")
llm=llm.bind_tools([search_options, make_option_table, plot_options_chain, human_assistance, toolTavilySearch, code_execution_tool])

# Define State
class State(TypedDict):
    messages: Annotated[list, add_messages]
    # Planner outputs
    ticker: str  # Stock ticker symbol
    date: str  # Expiration date or month
    strategy_type: str  # e.g., "conservative", "aggressive", "neutral"
    budget: float  # Maximum budget for the strategy
    risk_preference: str  # "low", "medium", "high"
    
    # Data Collector outputs
    options_data: dict  # Raw options chain data
    current_stock_price: float  # Current price of the underlying stock
    volatility: float  # Historical volatility (optional)
    
    # Total Checker outputs
    checked: bool  # Whether passed validation
    needs_retry: bool  # Whether needs to retry data collection
    needs_user_input: bool  # Whether needs to ask user for new parameters
    retry_count: int  # Number of retries attempted
    
    # Later stages
    intermediate_results: list  # Store results from strategy analyzer
    final_result: str  # Final decision and report


# Node 1: Planner
def planner(state: State) -> State:
    """
    Planner: Analyzes user input and extracts key parameters for options strategy
    Uses LLM to parse natural language and extract structured information
    """
    print("\n" + "="*70)
    print("[PLANNER] Analyzing user request...")
    print("="*70)
    
    messages = state["messages"]
    user_message = messages[-1].content if messages else "No input"
    
    # System prompt for structured extraction
    system_prompt = """You are an options trading assistant. Extract the following information from user requests:

1. **ticker**: Stock symbol (e.g., AAPL, TSLA, MSFT)
2. **date**: Expiration date in YYYY-MM-DD or month in YYYY-MM format
3. **strategy_type**: User's strategy preference (conservative/neutral/aggressive)
4. **budget**: Maximum budget in USD (if mentioned)
5. **risk_preference**: Risk tolerance (low/medium/high)

If information is missing, use these defaults:
- date: Next month in YYYY-MM format
- strategy_type: "neutral"
- budget: 5000.0
- risk_preference: "medium"

Respond ONLY with a valid JSON object. No other text.

Example response:
{
  "ticker": "AAPL",
  "date": "2025-11",
  "strategy_type": "conservative",
  "budget": 3000.0,
  "risk_preference": "low"
}"""
    
    # Call LLM to extract parameters
    extraction_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User request: {user_message}")
    ]
    
    response = llm.invoke(extraction_messages)
    
    try:
        # Parse LLM response as JSON
        extracted_data = json.loads(response.content)
        
        ticker = extracted_data.get("ticker", "").upper()
        date = extracted_data.get("date", "2025-11")
        strategy_type = extracted_data.get("strategy_type", "neutral")
        budget = float(extracted_data.get("budget", 5000.0))
        risk_preference = extracted_data.get("risk_preference", "medium")
        
        print(f"\n✅ Extracted Parameters:")
        print(f"   • Ticker: {ticker}")
        print(f"   • Date: {date}")
        print(f"   • Strategy Type: {strategy_type}")
        print(f"   • Budget: ${budget:,.2f}")
        print(f"   • Risk Preference: {risk_preference}")
        
        return {
            "ticker": ticker,
            "date": date,
            "strategy_type": strategy_type,
            "budget": budget,
            "risk_preference": risk_preference,
            "messages": [AIMessage(content=f"📋 Plan created for {ticker} options expiring {date}")]
        }
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Error parsing LLM response: {e}")
        print(f"Response was: {response.content}")
        
        # Fallback to defaults
        return {
            "ticker": "AAPL",
            "date": "2025-11",
            "strategy_type": "neutral",
            "budget": 5000.0,
            "risk_preference": "medium",
            "messages": [AIMessage(content="⚠️ Using default parameters")]
        }


# Node 2: Data Collector (Enhanced with retry support)
def data_collector(state: State) -> State:
    """
    Data Collector: Fetches options chain data and current stock price
    Supports automatic retry with higher limit if needed
    """
    print("\n" + "="*70)
    print("[DATA COLLECTOR] Fetching market data...")
    print("="*70)
    
    ticker = state.get("ticker", "AAPL")
    date = state.get("date", "2025-11")
    retry_count = state.get("retry_count", 0)
    needs_retry = state.get("needs_retry", False)
    
    # Determine limit based on retry status
    if needs_retry and retry_count == 0:
        # First retry: get 300 contracts
        limit = 300
        print(f"\n🔄 RETRY #{retry_count + 1}: Fetching MORE data...")
    elif needs_retry and retry_count > 0:
        # Subsequent retries: get more (up to 1000 max)
        limit = min(300 + retry_count * 200, 1000)
        print(f"\n🔄 RETRY #{retry_count + 1}: Fetching {limit} contracts...")
    else:
        # Initial fetch: get 100 contracts (for speed)
        limit = 100
    
    # 1. Fetch options chain data
    print(f"\n📊 Fetching options chain for {ticker} expiring {date} (limit={limit})...")
    options_data = fetch_options_data(ticker, date, limit)
    
    if options_data.get("error"):
        print(f"❌ Error fetching options: {options_data['error']}")
        return {
            "options_data": {},
            "current_stock_price": 0.0,
            "volatility": 0.0,
            "retry_count": retry_count,
            "messages": [AIMessage(content=f"❌ Failed to fetch options data: {options_data['error']}")]
        }
    
    num_contracts = options_data.get("count", 0)
    total_available = options_data.get("total_available", 0)
    print(f"✅ Found {num_contracts} contracts (out of {total_available} available)")
    
    # 2. Fetch current stock price
    print(f"\n💰 Fetching current price for {ticker}...")
    current_price = fetch_stock_price(ticker)
    
    if current_price > 0:
        print(f"✅ Current {ticker} price: ${current_price:.2f}")
    else:
        print(f"⚠️ Could not fetch current price, using estimate")
        current_price = estimate_price_from_options(options_data)
        print(f"📈 Estimated price: ${current_price:.2f}")
    
    # 3. Calculate simple volatility (optional)
    print(f"\n📉 Calculating volatility...")
    volatility = calculate_simple_volatility(options_data)
    print(f"✅ Estimated volatility: {volatility:.2%}")
    
    print("\n" + "="*70)
    print("✅ Data collection completed!")
    print("="*70)
    
    return {
        "options_data": options_data,
        "current_stock_price": current_price,
        "volatility": volatility,
        "retry_count": retry_count + 1 if needs_retry else retry_count,  # Increment retry count
        "needs_retry": False,  # Reset retry flag
        "messages": [AIMessage(content=f"📊 Collected data for {ticker}: {num_contracts} contracts, price ${current_price:.2f}")]
    }


# Helper functions for Data Collector
def fetch_options_data(ticker: str, date: str, limit: int = 100) -> dict:
    """Fetch options chain data from Polygon API"""
    url = "https://api.polygon.io/v3/reference/options/contracts"
    params = {
        "underlying_ticker": ticker.upper(),
        "limit": 1000,
        "apiKey": POLYGON_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            all_contracts = data.get('results', [])
            
            # Filter by date
            if len(date) == 7:  # Month format
                filtered = [c for c in all_contracts if c.get('expiration_date', '').startswith(date)]
            else:  # Specific date
                filtered = [c for c in all_contracts if c.get('expiration_date') == date]
            
            # Limit results
            limited_results = filtered[:limit] if len(filtered) > limit else filtered
            
            return {
                "results": limited_results,
                "count": len(limited_results),
                "total_available": len(filtered)
            }
        else:
            return {"error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"error": str(e)}


def fetch_stock_price(ticker: str) -> float:
    """Fetch current stock price from Polygon API"""
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    params = {"apiKey": POLYGON_API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                # Use closing price from previous day
                return float(results[0].get('c', 0))
        
        return 0.0
        
    except Exception as e:
        print(f"⚠️ Error fetching stock price: {e}")
        return 0.0


def estimate_price_from_options(options_data: dict) -> float:
    """Estimate stock price from options strike prices (fallback)"""
    contracts = options_data.get('results', [])
    if not contracts:
        return 0.0
    
    # Use median strike price as rough estimate
    strikes = [c.get('strike_price', 0) for c in contracts if c.get('strike_price')]
    if strikes:
        strikes.sort()
        return strikes[len(strikes) // 2]
    
    return 0.0


def calculate_simple_volatility(options_data: dict) -> float:
    """Calculate simple volatility estimate from options spread"""
    contracts = options_data.get('results', [])
    if not contracts:
        return 0.0
    
    strikes = [c.get('strike_price', 0) for c in contracts if c.get('strike_price')]
    if len(strikes) < 2:
        return 0.30  # Default 30%
    
    # Simple volatility estimate: (max_strike - min_strike) / median_strike
    strikes.sort()
    spread = strikes[-1] - strikes[0]
    median = strikes[len(strikes) // 2]
    
    if median > 0:
        volatility = spread / median
        return min(volatility, 1.0)  # Cap at 100%
    
    return 0.30


# Node 3: Total Checker (Enhanced with minimum data requirement)
def total_checker(state: State) -> State:
    """
    Total checker: Validates the collected data
    Requirements:
    - Must have at least 300 options contracts
    - Must have valid stock price
    - If insufficient data, will trigger retry
    """
    print("\n" + "="*70)
    print("[TOTAL CHECKER] Validating data...")
    print("="*70)
    
    options_data = state.get("options_data", {})
    current_price = state.get("current_stock_price", 0)
    
    # Get current data count
    current_count = options_data.get("count", 0)
    total_available = options_data.get("total_available", 0)
    
    # Minimum requirement: 300 contracts
    MIN_CONTRACTS = 300
    
    # Validation checks
    has_enough_data = current_count >= MIN_CONTRACTS
    has_price = current_price > 0
    can_get_more = total_available >= MIN_CONTRACTS  # Check if API has enough data
    
    print(f"\n📊 Data Status:")
    print(f"   • Current contracts: {current_count}")
    print(f"   • Required minimum: {MIN_CONTRACTS}")
    print(f"   • Total available: {total_available}")
    print(f"   • Stock price: ${current_price:.2f}")
    
    if has_enough_data and has_price:
        # Validation passed
        print(f"\n✅ Validation PASSED!")
        print(f"   • Sufficient data: {current_count} >= {MIN_CONTRACTS}")
        print(f"   • Valid stock price: ${current_price:.2f}")
        
        return {
            "checked": True,
            "messages": [AIMessage(content=f"✅ Validation passed: {current_count} contracts collected")]
        }
        
    elif not has_enough_data and can_get_more:
        # Not enough data, but can get more
        print(f"\n⚠️ Insufficient data: {current_count} < {MIN_CONTRACTS}")
        print(f"   📈 But {total_available} contracts available in total")
        print(f"   🔄 Will retry data collection with higher limit...")
        
        return {
            "checked": False,
            "needs_retry": True,  # Signal to retry
            "messages": [AIMessage(content=f"⚠️ Need more data: {current_count}/{MIN_CONTRACTS}. Retrying...")]
        }
        
    elif not has_enough_data and not can_get_more:
        # Not enough data and API doesn't have more
        print(f"\n❌ Insufficient data and cannot get more")
        print(f"   • Only {total_available} contracts available")
        print(f"   • Required: {MIN_CONTRACTS}")
        print(f"   💬 Will ask user for different parameters...")
        
        return {
            "checked": False,
            "needs_retry": False,
            "needs_user_input": True,  # Signal to ask user
            "messages": [AIMessage(content=f"❌ Only {total_available} contracts available, need {MIN_CONTRACTS}. Please try different date/ticker.")]
        }
        
    else:
        # No valid stock price
        print(f"\n❌ Validation failed: Invalid stock price")
        
        return {
            "checked": False,
            "needs_retry": False,
            "messages": [AIMessage(content="❌ Invalid stock price")]
        }


# Node 4: Aggregation (Summary Report)
def aggregation(state: State) -> State:
    """
    Aggregation: Summarizes all collected data
    """
    print("\n" + "="*70)
    print("[AGGREGATION] Generating summary report...")
    print("="*70)
    
    ticker = state.get("ticker", "N/A")
    date = state.get("date", "N/A")
    strategy_type = state.get("strategy_type", "N/A")
    budget = state.get("budget", 0)
    risk_preference = state.get("risk_preference", "N/A")
    
    options_data = state.get("options_data", {})
    current_price = state.get("current_stock_price", 0)
    volatility = state.get("volatility", 0)
    checked = state.get("checked", False)
    
    # Generate final report
    final_result = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    OPTIONS ANALYSIS SUMMARY                          ║
╚══════════════════════════════════════════════════════════════════════╝

📋 PARAMETERS:
   • Ticker: {ticker}
   • Expiration: {date}
   • Strategy Type: {strategy_type}
   • Budget: ${budget:,.2f}
   • Risk Preference: {risk_preference}

📊 MARKET DATA:
   • Current Stock Price: ${current_price:.2f}
   • Options Contracts Found: {options_data.get('count', 0)}
   • Estimated Volatility: {volatility:.2%}

✅ STATUS: {'Data collected successfully!' if checked else 'Data collection incomplete'}

💡 NEXT STEPS:
   - Strategy Analyzer will evaluate possible strategies
   - Risk Evaluator will assess risk/reward profiles
   - Decision Maker will recommend optimal strategy
"""
    
    print(final_result)
    
    return {
        "final_result": final_result,
        "messages": [AIMessage(content="✅ Summary report generated")]
    }


# Conditional routing: decide next step after total_checker
def should_reprocess(state: State) -> str:
    """
    Routing logic after total_checker:
    - If checked=True → go to aggregation (success path)
    - If needs_retry=True → go back to data_collector (retry path)
    - If needs_user_input=True → go to user_input_handler (ask user)
    - Otherwise → go to aggregation (failure path)
    """
    checked = state.get("checked", False)
    needs_retry = state.get("needs_retry", False)
    needs_user_input = state.get("needs_user_input", False)
    retry_count = state.get("retry_count", 0)
    
    MAX_RETRIES = 2  # Maximum 2 retries
    
    print(f"\n[ROUTER] Decision point:")
    print(f"   • checked={checked}")
    print(f"   • needs_retry={needs_retry}")
    print(f"   • needs_user_input={needs_user_input}")
    print(f"   • retry_count={retry_count}")
    
    if checked:
        print(f"   → Route: aggregation (✅ success)")
        return "aggregation"
    elif needs_retry and retry_count < MAX_RETRIES:
        print(f"   → Route: data_collector (🔄 retry #{retry_count + 1})")
        return "retry"
    elif needs_user_input or retry_count >= MAX_RETRIES:
        print(f"   → Route: aggregation (❌ failed, show error)")
        return "aggregation"
    else:
        print(f"   → Route: aggregation (default)")
        return "aggregation"


# Build the graph
def create_workflow():
    """
    Create the LangGraph workflow
    """
    graph_builder = StateGraph(State)
    
    # Add nodes
    graph_builder.add_node("planner", planner)
    graph_builder.add_node("data_collector", data_collector)
    graph_builder.add_node("total_checker", total_checker)
    graph_builder.add_node("aggregation", aggregation)
    
    # Add edges
    graph_builder.add_edge(START, "planner")
    graph_builder.add_edge("planner", "data_collector")
    graph_builder.add_edge("data_collector", "total_checker")
    
    # Conditional edge: based on checker result
    graph_builder.add_conditional_edges(
        "total_checker",
        should_reprocess,
        {
            "aggregation": "aggregation",  # Success or failure path
            "retry": "data_collector",     # Retry path - loop back to data collector
        }
    )
    
    graph_builder.add_edge("aggregation", END)
    
    # Compile with memory
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)
    
    return graph


# Main execution
if __name__ == "__main__":
    print("=" * 70)
    print("LangGraph Framework - Week 2")
    print("=" * 70)
    
    # Create the workflow
    graph = create_workflow()
    
    # Test run
    config = {"configurable": {"thread_id": "1"}}
    
    initial_input = {
        "messages": [HumanMessage(content="I want to trade AAPL options expiring in November 2025, my budget is $3000 and I prefer low risk strategies")]
    }
    
    print("\n🚀 Starting workflow...")
    print("=" * 70)
    
    # Run the graph
    result = graph.invoke(initial_input, config)
    
    print("\n" + "=" * 70)
    print("✅ WORKFLOW COMPLETED!")
    print("=" * 70)
    
    # Display summary
    print(f"\n{result.get('final_result', 'No result')}")
    
    # Display extracted parameters
    print("\n📌 Extracted Data:")
    print(f"   Ticker: {result.get('ticker', 'N/A')}")
    print(f"   Date: {result.get('date', 'N/A')}")
    print(f"   Budget: ${result.get('budget', 0):,.2f}")
    print(f"   Stock Price: ${result.get('current_stock_price', 0):.2f}")
    print(f"   Options Found: {result.get('options_data', {}).get('count', 0)}")
    print(f"   Volatility: {result.get('volatility', 0):.2%}")
