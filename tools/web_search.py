"""
Web Search Tools
Author: Leo Ji

Web search and human assistance tools.
"""

from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langgraph.types import interrupt


# Initialize Tavily Search tool
toolTavilySearch = TavilySearch(
    max_results=5,
    name="TavilySearch",
    description="Search the web for information. Useful for looking up company names, ticker symbols, or general information."
)


@tool
def human_assistance(query: str) -> str:
    """Request assistance from a human.
    
    Use this when you need human input or decision making.
    The execution will pause and wait for human response.
    
    Args:
        query: The question or information to present to the human
        
    Returns:
        Human's response
    """
    human_response = interrupt({"query": query})
    return human_response["data"]


__all__ = ['toolTavilySearch', 'human_assistance']

