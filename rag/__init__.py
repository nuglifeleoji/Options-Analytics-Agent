"""
RAG Knowledge Base Module
用于存储和检索期权数据的RAG系统
"""

from .rag_tools import (
    store_options_data,
    search_knowledge_base,
    get_historical_options,
    get_snapshot_by_id,
    rag_tools
)

from .rag_collection_tools import (
    collect_and_store_options,
    batch_collect_options,
    collect_date_range,
    check_missing_data,
    auto_update_watchlist,
    collection_tools
)

# 所有 RAG 工具（检索 + 采集）
all_rag_tools = rag_tools + collection_tools

__all__ = [
    # 检索工具
    'store_options_data',
    'search_knowledge_base',
    'get_historical_options',
    'get_snapshot_by_id',
    'rag_tools',
    # 采集工具
    'collect_and_store_options',
    'batch_collect_options',
    'collect_date_range',
    'check_missing_data',
    'auto_update_watchlist',
    'collection_tools',
    # 全部工具
    'all_rag_tools'
]

__version__ = '1.1.0'  # 添加了数据采集功能

