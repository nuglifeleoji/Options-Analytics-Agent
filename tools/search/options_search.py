"""
Options Search Tool
Author: Leo Ji

Search for options data from Polygon.io API with smart caching.
"""

import os
import json
import requests
from langchain_core.tools import tool
from config.settings import API_KEYS, LIMITS


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
        limit: Maximum number of contracts to return (default: 300, max: 1000)
        force_refresh: If True, skip cache and fetch fresh data from API (default: False)
    
    Returns:
        JSON string with options data including contract details
    """
    # Check cache first (unless force refresh)
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
    
    # Fetch from API
    api_key = API_KEYS.POLYGON_API_KEY
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


__all__ = ['search_options']

