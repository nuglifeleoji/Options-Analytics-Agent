"""
Batch Options Search Tool
Author: Leo Ji

Search for options data for multiple tickers with smart caching.
"""

import json
import time
from langchain_core.tools import tool
from .options_search import search_options


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


__all__ = ['batch_search_options']

