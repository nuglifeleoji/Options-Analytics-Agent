"""
Options Analysis Tools for LangGraph Integration
Author: Leo Ji

Provides professional options analysis and reporting tools for the agent.
"""

from langchain_core.tools import tool
from analysis.options_analyzer import analyzer
import json


@tool
def analyze_options_chain(ticker: str, options_data: str) -> str:
    """
    Perform comprehensive professional analysis on options chain data.
    
    This tool analyzes options data and provides insights on:
    - Market sentiment (bullish/bearish/neutral)
    - Call/Put ratio and interpretation
    - Strike price distribution
    - Key support/resistance levels
    - Risk assessment
    - Market structure analysis
    
    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA', 'AAPL') - REQUIRED FIRST
        options_data: JSON string containing options data (from search_options tool)
    
    Returns:
        Detailed analysis results in JSON format
    
    Example:
        data = search_options("NVDA", "2025-12", 500)
        analysis = analyze_options_chain("NVDA", data)
    
    IMPORTANT: Always provide ticker as the FIRST argument!
    """
    try:
        analysis = analyzer.analyze_options_chain(options_data, ticker)
        
        if "error" in analysis:
            return json.dumps(analysis, indent=2)
        
        # Format for easy reading
        summary = f"""
🔬 **OPTIONS CHAIN ANALYSIS COMPLETE**

📊 **Summary:**
• Total Contracts: {analysis['summary']['total_contracts']:,}
• Calls: {analysis['summary']['calls']:,} | Puts: {analysis['summary']['puts']:,}
• Call/Put Ratio: {analysis['summary']['call_put_ratio']}
• Interpretation: {analysis['summary']['interpretation']}

💭 **Sentiment:**
• Score: {analysis['sentiment_indicators']['sentiment_score']}/1.00
• Outlook: {analysis['sentiment_indicators']['interpretation']}
• Confidence: {analysis['sentiment_indicators']['confidence']}

⚠️ **Risk Level:** {analysis['risk_assessment']['risk_level']}

💡 Use 'generate_options_report' tool to get a full professional report.
"""
        
        # Store analysis for report generation
        analyzer.analysis_results = analysis
        
        return summary
        
    except Exception as e:
        return json.dumps({"error": f"Analysis failed: {str(e)}"}, indent=2)


@tool
def generate_options_report(ticker: str = None, format_type: str = "full") -> str:
    """
    Generate a professional options analysis report.
    
    This tool creates a comprehensive, professionally formatted report based on
    the most recent options chain analysis. The report includes:
    - Executive summary
    - Market sentiment analysis
    - Strike price analysis
    - Key support/resistance levels
    - Risk assessment
    - Conclusions and recommendations
    
    Args:
        ticker: (Optional) Ticker symbol for verification
        format_type: Report format - 'full' (default), 'summary', or 'json'
    
    Returns:
        Professional analysis report
    
    Note:
        Must run analyze_options_chain first to have data to report on.
    
    Example:
        # Step 1: Get and analyze data
        data = search_options("NVDA", "2025-12", 500)
        analyze_options_chain(data, "NVDA")
        
        # Step 2: Generate report
        report = generate_options_report("NVDA", "full")
    """
    try:
        if not analyzer.analysis_results:
            return "❌ No analysis data available. Please run 'analyze_options_chain' first."
        
        if format_type == "json":
            return json.dumps(analyzer.analysis_results, indent=2)
        elif format_type == "summary":
            return _generate_summary_report(analyzer.analysis_results)
        else:  # full
            return analyzer.generate_professional_report()
        
    except Exception as e:
        return f"❌ Error generating report: {str(e)}"


def _generate_summary_report(analysis: dict) -> str:
    """Generate a concise summary report."""
    summary = analysis.get('summary', {})
    sentiment = analysis.get('sentiment_indicators', {})
    risk = analysis.get('risk_assessment', {})
    
    return f"""
📈 **OPTIONS ANALYSIS SUMMARY - {analysis.get('ticker', 'N/A')}**
{'-'*60}

**Market Overview:**
• Total Contracts: {summary.get('total_contracts', 0):,}
• Call/Put Ratio: {summary.get('call_put_ratio', 'N/A')}
• Interpretation: {summary.get('interpretation', 'N/A')}

**Sentiment:**
• Outlook: {sentiment.get('interpretation', 'N/A')} ({sentiment.get('confidence', 'N/A')} confidence)
• Score: {sentiment.get('sentiment_score', 'N/A')}/1.00

**Risk:**
• Level: {risk.get('risk_level', 'N/A')}
• Put Concentration: {risk.get('put_percentage', 0):.1f}%

**Key Insight:**
{risk.get('description', 'N/A')}

💡 For detailed analysis, use format_type='full'
"""


@tool
def quick_sentiment_check(ticker: str, options_data: str) -> str:
    """
    Quick sentiment check from options data (faster than full analysis).
    
    This tool provides a rapid assessment of market sentiment based on
    call/put ratio and basic metrics. Use this when you need a quick read
    on market positioning without the full detailed analysis.
    
    Args:
        ticker: Stock ticker symbol - REQUIRED FIRST
        options_data: JSON string containing options data
    
    Returns:
        Quick sentiment summary
    
    Example:
        data = search_options("AAPL", "2025-11", 200)
        sentiment = quick_sentiment_check("AAPL", data)
    
    IMPORTANT: Always provide ticker as the FIRST argument!
    """
    try:
        data = json.loads(options_data)
        contracts = data.get('results', [])
        
        if not contracts:
            return "❌ No options data provided"
        
        # Count calls and puts
        calls = sum(1 for c in contracts if c.get('details', {}).get('contract_type', '').lower() == 'call')
        puts = sum(1 for c in contracts if c.get('details', {}).get('contract_type', '').lower() == 'put')
        
        if puts == 0:
            return f"🚀 **{ticker}** - EXTREMELY BULLISH (Only calls available)"
        
        ratio = calls / puts
        
        # Determine sentiment
        if ratio > 2.0:
            emoji = "🚀"
            sentiment = "Strong Bullish"
            description = "Heavy call activity suggests strong upside expectations"
        elif ratio > 1.5:
            emoji = "📈"
            sentiment = "Moderately Bullish"
            description = "More calls than puts, positive outlook"
        elif ratio > 0.8:
            emoji = "⚖️"
            sentiment = "Neutral"
            description = "Balanced activity, no clear directional bias"
        elif ratio > 0.5:
            emoji = "📉"
            sentiment = "Moderately Bearish"
            description = "More puts than calls, defensive positioning"
        else:
            emoji = "🔻"
            sentiment = "Strong Bearish"
            description = "Heavy put activity suggests downside concerns"
        
        return f"""
{emoji} **Quick Sentiment Check: {ticker}**

**Sentiment:** {sentiment}
**Call/Put Ratio:** {ratio:.2f}
**Contracts:** {calls:,} calls / {puts:,} puts

**Interpretation:** {description}

💡 For detailed analysis, use 'analyze_options_chain' tool.
"""
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


@tool
def compare_options_sentiment(ticker1: str, ticker1_data: str, ticker2: str, ticker2_data: str) -> str:
    """
    Compare sentiment between two tickers' options chains.
    
    This tool provides a side-by-side comparison of options positioning
    for two different stocks, helping identify relative sentiment.
    
    Args:
        ticker1: First ticker symbol - REQUIRED FIRST
        ticker1_data: Options data for first ticker (JSON string)
        ticker2: Second ticker symbol - REQUIRED THIRD
        ticker2_data: Options data for second ticker (JSON string)
    
    Returns:
        Comparative sentiment analysis
    
    Example:
        nvda_data = search_options("NVDA", "2025-12", 300)
        amd_data = search_options("AMD", "2025-12", 300)
        comparison = compare_options_sentiment("NVDA", nvda_data, "AMD", amd_data)
    
    IMPORTANT: Ticker symbols should come BEFORE their corresponding data!
    """
    try:
        # Analyze both
        analysis1 = analyzer.analyze_options_chain(ticker1_data, ticker1)
        analysis2 = analyzer.analyze_options_chain(ticker2_data, ticker2)
        
        if "error" in analysis1 or "error" in analysis2:
            return "❌ Error analyzing one or both tickers"
        
        sent1 = analysis1['sentiment_indicators']
        sent2 = analysis2['sentiment_indicators']
        
        ratio1 = analysis1['summary']['call_put_ratio']
        ratio2 = analysis2['summary']['call_put_ratio']
        
        # Determine relative sentiment
        if sent1['sentiment_score'] > sent2['sentiment_score']:
            more_bullish = ticker1
            less_bullish = ticker2
            difference = abs(sent1['sentiment_score'] - sent2['sentiment_score'])
        else:
            more_bullish = ticker2
            less_bullish = ticker1
            difference = abs(sent1['sentiment_score'] - sent2['sentiment_score'])
        
        return f"""
📊 **OPTIONS SENTIMENT COMPARISON**

**{ticker1}:**
• Sentiment: {sent1['interpretation']} ({sent1['confidence']} confidence)
• Score: {sent1['sentiment_score']}/1.00
• Call/Put Ratio: {ratio1}

**{ticker2}:**
• Sentiment: {sent2['interpretation']} ({sent2['confidence']} confidence)
• Score: {sent2['sentiment_score']}/1.00
• Call/Put Ratio: {ratio2}

**Relative Analysis:**
{more_bullish} shows more bullish positioning than {less_bullish}
Sentiment difference: {difference:.2f} points

**Interpretation:**
• {ticker1}: {analysis1['summary']['interpretation']}
• {ticker2}: {analysis2['summary']['interpretation']}
"""
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


# Export all tools
analysis_tools = [
    analyze_options_chain,
    generate_options_report,
    quick_sentiment_check,
    compare_options_sentiment
]

