"""
Options Analyzer - Professional Options Chain Analysis
Author: Leo Ji

Provides professional-grade analysis of options chains including:
- Market sentiment indicators
- Put/Call ratio analysis
- Strike distribution and key levels
- Volume and Open Interest analysis
- Options flow analysis
- Professional report generation
"""

import json
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import statistics


class OptionsAnalyzer:
    """Professional options chain analyzer."""
    
    def __init__(self):
        self.analysis_results = {}
    
    def _get_field(self, contract: Dict, field_name: str, default=None):
        """
        Helper to extract field from contract, handling both nested and flat structures.
        
        Polygon API sometimes returns:
        - Flat: {"contract_type": "call", "strike_price": 100, ...}
        - Nested: {"details": {"contract_type": "call", "strike_price": 100}, ...}
        """
        # Try nested structure first
        if 'details' in contract and field_name in contract['details']:
            return contract['details'][field_name]
        # Try flat structure
        elif field_name in contract:
            return contract[field_name]
        # Return default
        return default
    
    def analyze_options_chain(self, options_data: str, ticker: str) -> Dict[str, Any]:
        """
        Perform comprehensive analysis on options chain.
        
        Args:
            options_data: JSON string of options data (or dict)
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with complete analysis results
        """
        try:
            # Handle both JSON string and dict input
            if isinstance(options_data, str):
                try:
                    data = json.loads(options_data)
                except json.JSONDecodeError as e:
                    return {
                        "error": "Invalid JSON data",
                        "details": str(e),
                        "data_preview": options_data[:200] if len(options_data) > 200 else options_data
                    }
            elif isinstance(options_data, dict):
                data = options_data
            else:
                return {
                    "error": f"Invalid data type: expected str or dict, got {type(options_data).__name__}"
                }
            
            contracts = data.get('results', [])
            
            if not contracts:
                return {
                    "error": "No options data provided",
                    "data_keys": list(data.keys()),
                    "data_structure": str(data)[:300]
                }
            
            # Extract contract details
            calls, puts = self._separate_calls_puts(contracts)
            
            # Perform analyses
            analysis = {
                "ticker": ticker.upper(),
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_contracts": len(contracts),
                "summary": self._generate_summary(calls, puts),
                "sentiment_indicators": self._analyze_sentiment(calls, puts),
                "strike_analysis": self._analyze_strikes(calls, puts),
                "expiration_analysis": self._analyze_expirations(contracts),
                "key_levels": self._identify_key_levels(calls, puts),
                "market_structure": self._analyze_market_structure(calls, puts),
                "risk_assessment": self._assess_risk(calls, puts),
            }
            
            self.analysis_results = analysis
            return analysis
            
        except Exception as e:
            return {
                "error": f"Analysis failed: {str(e)}",
                "error_type": type(e).__name__,
                "ticker": ticker
            }
    
    def _separate_calls_puts(self, contracts: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Separate contracts into calls and puts."""
        calls = []
        puts = []
        
        for contract in contracts:
            contract_type = self._get_field(contract, 'contract_type', '').lower()
            
            if contract_type == 'call':
                calls.append(contract)
            elif contract_type == 'put':
                puts.append(contract)
        
        return calls, puts
    
    def _generate_summary(self, calls: List[Dict], puts: List[Dict]) -> Dict[str, Any]:
        """Generate high-level summary."""
        total = len(calls) + len(puts)
        
        return {
            "total_contracts": total,
            "calls": len(calls),
            "puts": len(puts),
            "call_put_ratio": round(len(calls) / len(puts), 2) if puts else None,
            "interpretation": self._interpret_call_put_ratio(len(calls), len(puts))
        }
    
    def _interpret_call_put_ratio(self, calls: int, puts: int) -> str:
        """Interpret call/put ratio for market sentiment."""
        if puts == 0:
            return "Extremely bullish - only calls available"
        
        ratio = calls / puts
        
        if ratio > 2.0:
            return "Strong bullish sentiment - significantly more calls than puts"
        elif ratio > 1.5:
            return "Moderately bullish - more calls than puts"
        elif ratio > 0.8:
            return "Neutral - balanced call/put distribution"
        elif ratio > 0.5:
            return "Moderately bearish - more puts than calls"
        else:
            return "Strong bearish sentiment - significantly more puts than calls"
    
    def _analyze_sentiment(self, calls: List[Dict], puts: List[Dict]) -> Dict[str, Any]:
        """Analyze market sentiment from options data."""
        sentiment = {
            "call_put_ratio": round(len(calls) / len(puts), 2) if puts else None,
            "sentiment_score": self._calculate_sentiment_score(calls, puts),
        }
        
        # Add interpretation
        score = sentiment["sentiment_score"]
        if score > 0.6:
            sentiment["interpretation"] = "Bullish"
            sentiment["confidence"] = "High" if score > 0.75 else "Moderate"
        elif score > 0.4:
            sentiment["interpretation"] = "Neutral"
            sentiment["confidence"] = "Moderate"
        else:
            sentiment["interpretation"] = "Bearish"
            sentiment["confidence"] = "High" if score < 0.25 else "Moderate"
        
        return sentiment
    
    def _calculate_sentiment_score(self, calls: List[Dict], puts: List[Dict]) -> float:
        """Calculate sentiment score (0-1, higher = more bullish)."""
        if not calls and not puts:
            return 0.5
        
        call_count = len(calls)
        put_count = len(puts)
        total = call_count + put_count
        
        # Simple ratio-based score
        score = call_count / total
        
        return round(score, 2)
    
    def _analyze_strikes(self, calls: List[Dict], puts: List[Dict]) -> Dict[str, Any]:
        """Analyze strike price distribution."""
        all_strikes = []
        call_strikes = []
        put_strikes = []
        
        for call in calls:
            strike = self._get_field(call, 'strike_price')
            if strike:
                all_strikes.append(strike)
                call_strikes.append(strike)
        
        for put in puts:
            strike = self._get_field(put, 'strike_price')
            if strike:
                all_strikes.append(strike)
                put_strikes.append(strike)
        
        if not all_strikes:
            return {"error": "No strike prices found"}
        
        return {
            "min_strike": min(all_strikes),
            "max_strike": max(all_strikes),
            "strike_range": max(all_strikes) - min(all_strikes),
            "median_strike": statistics.median(all_strikes),
            "call_strikes": {
                "min": min(call_strikes) if call_strikes else None,
                "max": max(call_strikes) if call_strikes else None,
                "median": statistics.median(call_strikes) if call_strikes else None
            },
            "put_strikes": {
                "min": min(put_strikes) if put_strikes else None,
                "max": max(put_strikes) if put_strikes else None,
                "median": statistics.median(put_strikes) if put_strikes else None
            }
        }
    
    def _analyze_expirations(self, contracts: List[Dict]) -> Dict[str, Any]:
        """Analyze expiration date distribution."""
        expirations = {}
        
        for contract in contracts:
            exp_date = self._get_field(contract, 'expiration_date')
            if exp_date:
                if exp_date not in expirations:
                    expirations[exp_date] = {"total": 0, "calls": 0, "puts": 0}
                
                expirations[exp_date]["total"] += 1
                
                contract_type = self._get_field(contract, 'contract_type', '').lower()
                    
                if contract_type == 'call':
                    expirations[exp_date]["calls"] += 1
                elif contract_type == 'put':
                    expirations[exp_date]["puts"] += 1
        
        # Sort by date
        sorted_expirations = dict(sorted(expirations.items()))
        
        # Find most active expiration
        most_active = max(expirations.items(), key=lambda x: x[1]["total"]) if expirations else (None, {})
        
        return {
            "unique_expirations": len(expirations),
            "expirations": sorted_expirations,
            "most_active_date": most_active[0],
            "most_active_count": most_active[1].get("total", 0)
        }
    
    def _identify_key_levels(self, calls: List[Dict], puts: List[Dict]) -> Dict[str, Any]:
        """Identify key support/resistance levels based on strike clustering."""
        all_contracts = calls + puts
        
        # Count contracts at each strike
        strike_counts = {}
        for contract in all_contracts:
            strike = self._get_field(contract, 'strike_price')
            if strike:
                strike_counts[strike] = strike_counts.get(strike, 0) + 1
        
        if not strike_counts:
            return {"error": "No strike data available"}
        
        # Sort by count to find most active strikes
        sorted_strikes = sorted(strike_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Top 5 most active strikes are key levels
        top_5 = sorted_strikes[:5]
        
        return {
            "key_strike_levels": [
                {
                    "strike": strike,
                    "contracts": count,
                    "significance": "Very High" if i == 0 else "High" if i < 3 else "Moderate"
                }
                for i, (strike, count) in enumerate(top_5)
            ],
            "interpretation": f"The strike ${top_5[0][0]} shows highest concentration with {top_5[0][1]} contracts, suggesting a key level"
        }
    
    def _analyze_market_structure(self, calls: List[Dict], puts: List[Dict]) -> Dict[str, Any]:
        """Analyze overall market structure from options positioning."""
        # Use _get_field for consistent data extraction
        call_strikes = [self._get_field(c, 'strike_price') for c in calls]
        call_strikes = [s for s in call_strikes if s is not None]
        
        put_strikes = [self._get_field(p, 'strike_price') for p in puts]
        put_strikes = [s for s in put_strikes if s is not None]
        
        if not call_strikes or not put_strikes:
            return {"error": "Insufficient data"}
        
        avg_call_strike = statistics.mean(call_strikes)
        avg_put_strike = statistics.mean(put_strikes)
        
        # Analyze skew
        skew = "Call-heavy" if avg_call_strike > avg_put_strike else "Put-heavy"
        skew_diff = abs(avg_call_strike - avg_put_strike)
        
        return {
            "average_call_strike": round(avg_call_strike, 2),
            "average_put_strike": round(avg_put_strike, 2),
            "skew": skew,
            "skew_magnitude": round(skew_diff, 2),
            "interpretation": f"Options positioning is {skew.lower()} with ${skew_diff:.2f} differential"
        }
    
    def _assess_risk(self, calls: List[Dict], puts: List[Dict]) -> Dict[str, Any]:
        """Assess market risk based on options positioning."""
        total = len(calls) + len(puts)
        
        # Risk indicators
        put_ratio = len(puts) / total if total > 0 else 0
        
        # Determine risk level
        if put_ratio > 0.6:
            risk_level = "Elevated"
            risk_description = "High put concentration suggests defensive positioning or hedging activity"
        elif put_ratio > 0.4:
            risk_level = "Moderate"
            risk_description = "Balanced options activity suggests neutral market outlook"
        else:
            risk_level = "Low"
            risk_description = "Call-heavy positioning suggests bullish outlook with lower perceived risk"
        
        return {
            "risk_level": risk_level,
            "put_percentage": round(put_ratio * 100, 1),
            "call_percentage": round((1 - put_ratio) * 100, 1),
            "description": risk_description
        }
    
    def generate_professional_report(self, analysis: Dict[str, Any] = None) -> str:
        """
        Generate a professional-grade analysis report.
        
        Args:
            analysis: Analysis results (uses last analysis if not provided)
            
        Returns:
            Formatted professional report
        """
        if analysis is None:
            analysis = self.analysis_results
        
        if not analysis or "error" in analysis:
            return "❌ Error: No analysis data available"
        
        # Generate report sections
        report = self._build_report_header(analysis)
        report += self._build_executive_summary(analysis)
        report += self._build_sentiment_section(analysis)
        report += self._build_strike_analysis_section(analysis)
        report += self._build_key_levels_section(analysis)
        report += self._build_risk_assessment_section(analysis)
        report += self._build_conclusions_section(analysis)
        
        return report
    
    def _build_report_header(self, analysis: Dict[str, Any]) -> str:
        """Build report header."""
        ticker = analysis.get('ticker', 'N/A')
        date = analysis.get('analysis_date', 'N/A')
        
        return f"""
{'='*80}
                    OPTIONS CHAIN ANALYSIS REPORT
{'='*80}

Ticker: {ticker}
Analysis Date: {date}
Report Generated By: Options Analyzer v1.0

{'='*80}

"""
    
    def _build_executive_summary(self, analysis: Dict[str, Any]) -> str:
        """Build executive summary section."""
        summary = analysis.get('summary', {})
        
        return f"""
## EXECUTIVE SUMMARY

Total Contracts Analyzed: {summary.get('total_contracts', 0):,}
  • Call Options: {summary.get('calls', 0):,}
  • Put Options: {summary.get('puts', 0):,}
  • Call/Put Ratio: {summary.get('call_put_ratio', 'N/A')}

Market Interpretation: {summary.get('interpretation', 'N/A')}

"""
    
    def _build_sentiment_section(self, analysis: Dict[str, Any]) -> str:
        """Build sentiment analysis section."""
        sentiment = analysis.get('sentiment_indicators', {})
        
        return f"""
## MARKET SENTIMENT ANALYSIS

Sentiment Score: {sentiment.get('sentiment_score', 'N/A')} / 1.00
Interpretation: {sentiment.get('interpretation', 'N/A')}
Confidence Level: {sentiment.get('confidence', 'N/A')}

📊 The sentiment score indicates a **{sentiment.get('interpretation', 'N/A')}** outlook with 
{sentiment.get('confidence', 'N/A').lower()} confidence based on options positioning.

"""
    
    def _build_strike_analysis_section(self, analysis: Dict[str, Any]) -> str:
        """Build strike analysis section."""
        strikes = analysis.get('strike_analysis', {})
        
        if 'error' in strikes:
            return "\n## STRIKE PRICE ANALYSIS\n\nInsufficient data for strike analysis.\n\n"
        
        # Helper to format None-safe values
        def fmt(value, default=0):
            return f"${value:.2f}" if value is not None else f"${default:.2f}"
        
        # Get call and put strikes
        call_strikes = strikes.get('call_strikes', {})
        put_strikes = strikes.get('put_strikes', {})
        
        return f"""
## STRIKE PRICE ANALYSIS

Strike Price Range: {fmt(strikes.get('min_strike'))} - {fmt(strikes.get('max_strike'))}
Range Span: {fmt(strikes.get('strike_range'))}
Median Strike: {fmt(strikes.get('median_strike'))}

Call Options:
  • Highest Strike: {fmt(call_strikes.get('max')) if call_strikes.get('max') else 'N/A'}
  • Lowest Strike: {fmt(call_strikes.get('min')) if call_strikes.get('min') else 'N/A'}
  • Median Strike: {fmt(call_strikes.get('median')) if call_strikes.get('median') else 'N/A'}

Put Options:
  • Highest Strike: {fmt(put_strikes.get('max')) if put_strikes.get('max') else 'N/A'}
  • Lowest Strike: {fmt(put_strikes.get('min')) if put_strikes.get('min') else 'N/A'}
  • Median Strike: {fmt(put_strikes.get('median')) if put_strikes.get('median') else 'N/A'}

"""
    
    def _build_key_levels_section(self, analysis: Dict[str, Any]) -> str:
        """Build key levels section."""
        levels = analysis.get('key_levels', {})
        
        if 'error' in levels:
            return "\n## KEY SUPPORT/RESISTANCE LEVELS\n\nInsufficient data for level identification.\n\n"
        
        section = "\n## KEY SUPPORT/RESISTANCE LEVELS\n\n"
        section += "Based on strike price concentration, the following levels are significant:\n\n"
        
        for i, level in enumerate(levels.get('key_strike_levels', []), 1):
            section += f"{i}. ${level['strike']:.2f} - {level['contracts']} contracts ({level['significance']} significance)\n"
        
        section += f"\n💡 {levels.get('interpretation', '')}\n\n"
        
        return section
    
    def _build_risk_assessment_section(self, analysis: Dict[str, Any]) -> str:
        """Build risk assessment section."""
        risk = analysis.get('risk_assessment', {})
        
        return f"""
## RISK ASSESSMENT

Risk Level: **{risk.get('risk_level', 'N/A')}**
Put Concentration: {risk.get('put_percentage', 0):.1f}%
Call Concentration: {risk.get('call_percentage', 0):.1f}%

Analysis: {risk.get('description', 'N/A')}

"""
    
    def _build_conclusions_section(self, analysis: Dict[str, Any]) -> str:
        """Build conclusions section."""
        sentiment = analysis.get('sentiment_indicators', {})
        risk = analysis.get('risk_assessment', {})
        
        return f"""
## CONCLUSIONS & RECOMMENDATIONS

1. **Market Outlook**: The options market is showing a **{sentiment.get('interpretation', 'N/A').lower()}** 
   bias based on the current positioning.

2. **Risk Profile**: Current risk level is assessed as **{risk.get('risk_level', 'N/A').lower()}**, 
   suggesting {self._risk_to_action(risk.get('risk_level', 'Moderate'))}.

3. **Key Observations**:
   - Options positioning reflects {sentiment.get('confidence', 'moderate').lower()} confidence in 
     the {sentiment.get('interpretation', 'neutral').lower()} outlook
   - Strike distribution suggests key levels that may act as support/resistance
   - Current call/put ratio indicates {self._ratio_to_behavior(analysis.get('summary', {}).get('call_put_ratio'))}

{'='*80}
End of Report
{'='*80}
"""
    
    def _risk_to_action(self, risk_level: str) -> str:
        """Convert risk level to actionable insight."""
        if risk_level == "Elevated":
            return "caution and defensive positioning may be appropriate"
        elif risk_level == "Moderate":
            return "balanced approach with attention to key levels"
        else:
            return "market participants are relatively comfortable with upside exposure"
    
    def _ratio_to_behavior(self, ratio: Optional[float]) -> str:
        """Convert call/put ratio to market behavior."""
        if ratio is None:
            return "insufficient data for behavior analysis"
        
        if ratio > 1.5:
            return "bullish positioning with upside focus"
        elif ratio > 0.8:
            return "balanced positioning with no clear directional bias"
        else:
            return "defensive positioning with downside hedging"


# Global analyzer instance
analyzer = OptionsAnalyzer()

