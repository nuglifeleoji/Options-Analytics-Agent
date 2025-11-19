"""
Performance Monitor Tool - Execution Efficiency and Token Usage Tracking

This module provides tools to monitor and report:
- Execution time for agent operations
- Token usage (prompt tokens, completion tokens, total tokens)
- Cost estimation based on token usage
- Historical performance metrics

Author: Leo Ji
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
from langchain_core.tools import tool


class PerformanceMonitor:
    """
    Tracks performance metrics for agent operations.
    
    Monitors:
    - Execution time for each query
    - Token usage (prompt, completion, total)
    - Cost estimation
    - Tool usage statistics
    """
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.metrics: List[Dict[str, Any]] = []
        self.current_session = {
            "start_time": None,
            "end_time": None,
            "query": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "tools_used": [],
            "execution_time": 0.0
        }
        
        # Token costs (USD per 1M tokens) - GPT-4o-mini pricing
        self.token_costs = {
            "gpt-4o-mini": {
                "prompt": 0.150,      # $0.150 per 1M input tokens
                "completion": 0.600   # $0.600 per 1M output tokens
            },
            "gpt-4o": {
                "prompt": 2.50,
                "completion": 10.00
            }
        }
        
        self.current_model = "gpt-4o-mini"
    
    def start_tracking(self, query: str):
        """
        Start tracking a new query.
        
        Args:
            query: The user query being processed
        """
        self.current_session = {
            "start_time": time.time(),
            "end_time": None,
            "query": query,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "tools_used": [],
            "execution_time": 0.0
        }
    
    def record_tokens(self, prompt_tokens: int, completion_tokens: int):
        """
        Record token usage for the current session.
        
        Args:
            prompt_tokens: Number of prompt (input) tokens
            completion_tokens: Number of completion (output) tokens
        """
        self.current_session["prompt_tokens"] += prompt_tokens
        self.current_session["completion_tokens"] += completion_tokens
        self.current_session["total_tokens"] = (
            self.current_session["prompt_tokens"] + 
            self.current_session["completion_tokens"]
        )
    
    def record_tool_usage(self, tool_name: str):
        """
        Record that a tool was used.
        
        Args:
            tool_name: Name of the tool that was called
        """
        self.current_session["tools_used"].append(tool_name)
    
    def stop_tracking(self):
        """
        Stop tracking and save metrics for current session.
        """
        if self.current_session["start_time"]:
            self.current_session["end_time"] = time.time()
            self.current_session["execution_time"] = (
                self.current_session["end_time"] - 
                self.current_session["start_time"]
            )
            
            # Add timestamp
            self.current_session["timestamp"] = datetime.now().isoformat()
            
            # Calculate cost
            cost = self._calculate_cost(
                self.current_session["prompt_tokens"],
                self.current_session["completion_tokens"]
            )
            self.current_session["estimated_cost"] = cost
            
            # Save to metrics history
            self.metrics.append(self.current_session.copy())
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate estimated cost based on token usage.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
        
        Returns:
            Estimated cost in USD
        """
        costs = self.token_costs.get(self.current_model, self.token_costs["gpt-4o-mini"])
        
        prompt_cost = (prompt_tokens / 1_000_000) * costs["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * costs["completion"]
        
        return prompt_cost + completion_cost
    
    def get_current_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the current/last query.
        
        Returns:
            Dictionary with current performance metrics
        """
        if not self.current_session["start_time"]:
            return {"message": "No active tracking session"}
        
        return {
            "query": self.current_session["query"],
            "execution_time": f"{self.current_session['execution_time']:.2f}s",
            "tokens": {
                "prompt": self.current_session["prompt_tokens"],
                "completion": self.current_session["completion_tokens"],
                "total": self.current_session["total_tokens"]
            },
            "estimated_cost": f"${self.current_session.get('estimated_cost', 0):.6f}",
            "tools_used": self.current_session["tools_used"],
            "model": self.current_model
        }
    
    def get_session_summary(self, num_recent: int = 10) -> Dict[str, Any]:
        """
        Get summary statistics for recent sessions.
        
        Args:
            num_recent: Number of recent sessions to include
        
        Returns:
            Summary statistics dictionary
        """
        if not self.metrics:
            return {"message": "No performance data available yet"}
        
        recent = self.metrics[-num_recent:]
        
        total_tokens = sum(m["total_tokens"] for m in recent)
        total_cost = sum(m.get("estimated_cost", 0) for m in recent)
        avg_execution_time = sum(m["execution_time"] for m in recent) / len(recent)
        
        # Tool usage statistics
        tool_counts = defaultdict(int)
        for m in recent:
            for tool in m["tools_used"]:
                tool_counts[tool] += 1
        
        return {
            "total_queries": len(self.metrics),
            "recent_queries": len(recent),
            "total_tokens_used": total_tokens,
            "total_cost": f"${total_cost:.6f}",
            "average_execution_time": f"{avg_execution_time:.2f}s",
            "most_used_tools": dict(sorted(
                tool_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]),
            "model": self.current_model
        }
    
    def get_detailed_history(self, num_recent: int = 5) -> List[Dict[str, Any]]:
        """
        Get detailed history of recent queries.
        
        Args:
            num_recent: Number of recent queries to return
        
        Returns:
            List of detailed metrics for recent queries
        """
        if not self.metrics:
            return []
        
        recent = self.metrics[-num_recent:]
        
        return [
            {
                "timestamp": m.get("timestamp", "N/A"),
                "query": m["query"][:50] + "..." if len(m["query"]) > 50 else m["query"],
                "execution_time": f"{m['execution_time']:.2f}s",
                "tokens": m["total_tokens"],
                "cost": f"${m.get('estimated_cost', 0):.6f}",
                "tools": ", ".join(m["tools_used"]) if m["tools_used"] else "None"
            }
            for m in recent
        ]


# Global performance monitor instance
monitor = PerformanceMonitor()


@tool
def get_performance_stats(mode: str = "current") -> str:
    """
    Get performance statistics and efficiency metrics for the agent.
    
    This tool provides insights into:
    - Execution time for queries
    - Token usage (prompt, completion, total)
    - Estimated costs
    - Tool usage statistics
    
    Args:
        mode: Type of statistics to retrieve:
              - "current": Stats for the last query only
              - "summary": Aggregate stats for recent queries (last 10)
              - "history": Detailed history of last 5 queries
              - "all": All available statistics
    
    Returns:
        JSON string with performance metrics
    
    Example usage:
        User: "How efficient was my last query?"
        → get_performance_stats(mode="current")
        
        User: "Show me overall performance stats"
        → get_performance_stats(mode="summary")
        
        User: "What's my token usage history?"
        → get_performance_stats(mode="history")
    """
    try:
        if mode == "current":
            stats = monitor.get_current_stats()
            
            if "message" in stats:
                return json.dumps(stats, indent=2)
            
            # Format nicely
            result = f"""
📊 Current Query Performance:

⏱️  Execution Time: {stats['execution_time']}

🎯 Token Usage:
   • Prompt tokens: {stats['tokens']['prompt']:,}
   • Completion tokens: {stats['tokens']['completion']:,}
   • Total tokens: {stats['tokens']['total']:,}

💰 Estimated Cost: {stats['estimated_cost']}

🛠️  Tools Used: {', '.join(stats['tools_used']) if stats['tools_used'] else 'None'}

🤖 Model: {stats['model']}
"""
            return result.strip()
        
        elif mode == "summary":
            summary = monitor.get_session_summary()
            
            if "message" in summary:
                return json.dumps(summary, indent=2)
            
            result = f"""
📈 Performance Summary (Last {summary['recent_queries']} Queries):

📝 Total Queries: {summary['total_queries']}
🎯 Total Tokens: {summary['total_tokens_used']:,}
💰 Total Cost: {summary['total_cost']}
⏱️  Avg Execution Time: {summary['average_execution_time']}

🛠️  Most Used Tools:
"""
            for tool, count in summary['most_used_tools'].items():
                result += f"   • {tool}: {count} times\n"
            
            result += f"\n🤖 Model: {summary['model']}"
            
            return result.strip()
        
        elif mode == "history":
            history = monitor.get_detailed_history()
            
            if not history:
                return json.dumps({"message": "No history available"}, indent=2)
            
            result = "📜 Performance History (Last 5 Queries):\n\n"
            
            for i, entry in enumerate(history, 1):
                result += f"""
{i}. Query: {entry['query']}
   Time: {entry['timestamp'][:19]}
   Duration: {entry['execution_time']}
   Tokens: {entry['tokens']:,}
   Cost: {entry['cost']}
   Tools: {entry['tools']}
"""
            
            return result.strip()
        
        elif mode == "all":
            current = monitor.get_current_stats()
            summary = monitor.get_session_summary()
            
            result = {
                "current_query": current,
                "summary": summary
            }
            
            return json.dumps(result, indent=2)
        
        else:
            return json.dumps({
                "error": f"Unknown mode: {mode}",
                "valid_modes": ["current", "summary", "history", "all"]
            }, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to get performance stats: {str(e)}"
        }, indent=2)


# Export the tool and monitor
__all__ = ['get_performance_stats', 'monitor']

