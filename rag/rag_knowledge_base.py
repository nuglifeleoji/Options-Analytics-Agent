"""
RAG Knowledge Base - Core Implementation
核心实现：ChromaDB + SQLite 混合存储和检索
"""
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from openai import OpenAI

from rag_config import (
    CHROMA_DB_PATH,
    SQLITE_DB_PATH,
    CHROMA_COLLECTION_NAME,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_API_KEY,
    DISTANCE_METRIC,
    DEFAULT_SEARCH_LIMIT,
    SIMILARITY_THRESHOLD
)

# ==================== 初始化 ====================

# OpenAI Client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ChromaDB Client
chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_PATH,
    settings=Settings(anonymized_telemetry=False)
)

# ==================== Embedding 生成 ====================

def generate_embedding(text: str) -> List[float]:
    """
    使用 OpenAI 生成文本的 embedding
    
    Args:
        text: 要生成 embedding 的文本
        
    Returns:
        Embedding 向量（1536维）
    """
    try:
        response = openai_client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        raise

def create_document_text(options_data: dict, ticker: str, date: str) -> str:
    """
    从期权数据创建用于 embedding 的文本描述
    
    Args:
        options_data: 期权数据字典
        ticker: 股票代码
        date: 日期
        
    Returns:
        文本描述
    """
    results = options_data.get("results", [])
    count = options_data.get("count", 0)
    
    # 统计信息
    calls = sum(1 for r in results if r.get("contract_type", "").lower() == "call")
    puts = sum(1 for r in results if r.get("contract_type", "").lower() == "put")
    
    # 执行价范围
    strikes = [r.get("strike_price", 0) for r in results if r.get("strike_price")]
    strike_min = min(strikes) if strikes else 0
    strike_max = max(strikes) if strikes else 0
    
    # 生成描述文本
    text = f"""
    Stock Options Data for {ticker}
    Date: {date}
    Total Contracts: {count}
    Call Options: {calls}
    Put Options: {puts}
    Strike Price Range: ${strike_min:.2f} to ${strike_max:.2f}
    Call/Put Ratio: {calls/puts if puts > 0 else 'N/A'}
    Data Source: Polygon.io
    """
    
    return text.strip()

# ==================== ChromaDB 操作 ====================

def get_or_create_collection():
    """获取或创建 ChromaDB collection
    
    重要：不使用 embedding_function，因为我们手动生成 embedding
    """
    try:
        collection = chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={
                "hnsw:space": DISTANCE_METRIC
            },
            # 不指定 embedding_function，手动提供 embeddings
            embedding_function=None
        )
        return collection
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        raise

def store_to_chromadb(
    snapshot_id: str,
    text: str,
    embedding: List[float],
    metadata: dict
) -> bool:
    """
    存储数据到 ChromaDB
    
    Args:
        snapshot_id: 快照ID
        text: 文本描述
        embedding: 向量
        metadata: 元数据
        
    Returns:
        是否成功
    """
    try:
        collection = get_or_create_collection()
        
        # 调试信息
        print(f"  → Snapshot ID: {snapshot_id}")
        print(f"  → Embedding dimension: {len(embedding)}")
        print(f"  → Document length: {len(text)} chars")
        print(f"  → Metadata keys: {list(metadata.keys())}")
        
        # 添加 snapshot_id 到 metadata（用于异动检测）
        chroma_metadata = {
            **metadata,
            "snapshot_id": snapshot_id
        }
        
        collection.add(
            ids=[snapshot_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[chroma_metadata]
        )
        
        print(f"  ✅ Stored to ChromaDB successfully")
        return True
    except Exception as e:
        print(f"❌ Error storing to ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return False

def search_chromadb(
    query_text: str = None,
    query_embedding: List[float] = None,
    limit: int = DEFAULT_SEARCH_LIMIT,
    where: dict = None
) -> List[Dict[str, Any]]:
    """
    在 ChromaDB 中搜索
    
    Args:
        query_text: 查询文本（会自动生成embedding）
        query_embedding: 直接提供 embedding
        limit: 返回数量
        where: 元数据过滤条件
        
    Returns:
        搜索结果列表
    """
    try:
        collection = get_or_create_collection()
        
        # 如果提供了文本，生成embedding
        if query_text and not query_embedding:
            query_embedding = generate_embedding(query_text)
        
        # 搜索
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )
        
        # 格式化结果
        formatted_results = []
        if results and results['ids']:
            for i, snapshot_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    "id": snapshot_id,
                    "distance": results['distances'][0][i],
                    "similarity": 1 - results['distances'][0][i],  # 转换为相似度
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i]
                })
        
        return formatted_results
        
    except Exception as e:
        print(f"❌ Error searching ChromaDB: {e}")
        return []

# ==================== SQLite 操作 ====================

def init_sqlite_db():
    """初始化 SQLite 数据库"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    # 创建快照表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS options_snapshots (
        id TEXT PRIMARY KEY,
        ticker TEXT NOT NULL,
        date TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        total_contracts INTEGER,
        calls_count INTEGER,
        puts_count INTEGER,
        strike_min REAL,
        strike_max REAL,
        avg_strike REAL,
        data_json TEXT NOT NULL,
        metadata_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建索引
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_ticker_date 
    ON options_snapshots(ticker, date)
    ''')
    
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_timestamp 
    ON options_snapshots(timestamp)
    ''')
    
    conn.commit()
    conn.close()
    print("✅ SQLite database initialized")

def store_to_sqlite(
    snapshot_id: str,
    ticker: str,
    date: str,
    options_data: dict,
    metadata: dict
) -> bool:
    """
    存储数据到 SQLite
    
    Args:
        snapshot_id: 快照ID
        ticker: 股票代码
        date: 日期
        options_data: 期权数据
        metadata: 元数据
        
    Returns:
        是否成功
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO options_snapshots
        (id, ticker, date, timestamp, total_contracts, calls_count, puts_count,
         strike_min, strike_max, avg_strike, data_json, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot_id,
            ticker,
            date,
            metadata.get("timestamp"),
            metadata.get("total_contracts"),
            metadata.get("calls_count"),
            metadata.get("puts_count"),
            metadata.get("strike_min"),
            metadata.get("strike_max"),
            metadata.get("avg_strike"),
            json.dumps(options_data),
            json.dumps(metadata)
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error storing to SQLite: {e}")
        return False

def get_from_sqlite(snapshot_id: str) -> Optional[dict]:
    """从 SQLite 获取数据"""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT data_json, metadata_json FROM options_snapshots
        WHERE id = ?
        ''', (snapshot_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "data": json.loads(result[0]),
                "metadata": json.loads(result[1])
            }
        return None
        
    except Exception as e:
        print(f"❌ Error retrieving from SQLite: {e}")
        return None

def query_sqlite(
    ticker: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100
) -> List[dict]:
    """
    从 SQLite 查询数据
    
    Args:
        ticker: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        limit: 限制数量
        
    Returns:
        查询结果列表
    """
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        query = "SELECT * FROM options_snapshots WHERE 1=1"
        params = []
        
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            # 解析 JSON 字段
            if result.get('data_json'):
                result['data'] = json.loads(result['data_json'])
            if result.get('metadata_json'):
                result['metadata'] = json.loads(result['metadata_json'])
            results.append(result)
        
        conn.close()
        return results
        
    except Exception as e:
        print(f"❌ Error querying SQLite: {e}")
        return []


def extract_metadata(options_data: dict, ticker: str, date: str) -> dict:
    """提取元数据"""
    results = options_data.get("results", [])
    
    calls = [r for r in results if r.get("contract_type", "").lower() == "call"]
    puts = [r for r in results if r.get("contract_type", "").lower() == "put"]
    
    strikes = [r.get("strike_price", 0) for r in results if r.get("strike_price")]
    
    return {
        "ticker": ticker,
        "date": date,
        "timestamp": datetime.now().isoformat(),
        "total_contracts": len(results),
        "calls_count": len(calls),
        "puts_count": len(puts),
        "strike_min": min(strikes) if strikes else 0,
        "strike_max": max(strikes) if strikes else 0,
        "avg_strike": sum(strikes) / len(strikes) if strikes else 0,
        "data_source": "polygon.io"
    }

def detect_options_anomaly(
    ticker: str,
    reference_date: str,
    comparison_dates: Optional[List[str]] = None,
    min_similarity: float = 0.0,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """
    检测 options 数据的异动，通过向量相似度对比。
    
    使用 ChromaDB 的向量相似度来找出与参考日期最不相似的数据点，
    这些可能代表市场的异动或者异常交易活动。
    
    Args:
        ticker: 股票代码
        reference_date: 参考日期（基准）
        comparison_dates: 要对比的日期列表（可选，如果为None则对比所有历史数据）
        min_similarity: 最小相似度阈值（0-1），低于此值才视为异动
        max_results: 返回最多多少个异动结果
        
    Returns:
        异动列表，按相似度从低到高排序（相似度越低 = 异动越大）
    """
    try:
        # 获取 ChromaDB collection
        collection = get_or_create_collection()
        
        # 步骤1: 获取参考数据
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        
        # 从 SQLite 获取参考数据
        cursor.execute('''
            SELECT id, ticker, date, total_contracts, calls_count, puts_count,
                   strike_min, strike_max, avg_strike, data_json, timestamp
            FROM options_snapshots
            WHERE ticker = ? AND date = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (ticker.upper(), reference_date))
        
        reference_row = cursor.fetchone()
        
        if not reference_row:
            conn.close()
            return [{
                "error": f"No reference data found for {ticker} on {reference_date}",
                "suggestion": "Try collecting data first using collect_and_store_options"
            }]
        
        reference_id = reference_row[0]
        ref_calls = reference_row[4]
        ref_puts = reference_row[5]
        ref_strike_min = reference_row[6]
        ref_strike_max = reference_row[7]
        ref_avg_strike = reference_row[8]
        ref_total = reference_row[3]
        
        # 从 ChromaDB 获取参考向量和文档
        reference_result = collection.get(
            ids=[reference_id],
            include=['documents', 'embeddings']  # 同时获取文档和 embedding
        )
        
        if not reference_result or not reference_result['documents']:
            conn.close()
            return [{"error": f"Reference snapshot {reference_id} not found in vector database"}]
        
        reference_doc = reference_result['documents'][0]
        
        # 获取存储的 embedding（1536维）
        embeddings = reference_result.get('embeddings')
        
        # 检查 embeddings 是否存在
        if embeddings is None or len(embeddings) == 0:
            conn.close()
            return [{"error": f"Reference embedding not found for {reference_id}"}]
        
        reference_embedding = embeddings[0]
        
        # 检查 embedding 是否有效
        if reference_embedding is None or len(reference_embedding) == 0:
            conn.close()
            return [{"error": f"Reference embedding is empty for {reference_id}"}]
        
        print(f"  → Reference embedding dimension: {len(reference_embedding)}")
        
        # 步骤2: 构建查询条件
        where_filter = {"ticker": ticker.upper()}
        
        # 步骤3: 进行相似度搜索
        # 🔥 关键修复：使用 query_embeddings 而不是 query_texts
        # 这样就不会触发 ChromaDB 的 embedding function
        similar_results = collection.query(
            query_embeddings=[reference_embedding],  # ← 使用手动提供的 1536 维 embedding
            n_results=50,
            where=where_filter
        )
        
        # 步骤4: 处理结果
        anomalies = []
        
        if similar_results and similar_results['metadatas'] and similar_results['distances']:
            for i, (metadata, distance) in enumerate(zip(
                similar_results['metadatas'][0], 
                similar_results['distances'][0]
            )):
                snapshot_id = metadata.get('snapshot_id')
                
                # 跳过参考数据本身
                if snapshot_id == reference_id:
                    continue
                
                # 跳过不在对比日期列表中的数据（如果指定了列表）
                snapshot_date = metadata.get('date')
                if comparison_dates and snapshot_date not in comparison_dates:
                    continue
                
                # 计算相似度分数 (1 - distance)
                # ChromaDB 使用余弦距离，范围 [0, 2]
                # 0 = 完全相同, 2 = 完全相反
                similarity_score = 1 - (distance / 2)
                
                # 只返回相似度大于等于阈值的
                if similarity_score < min_similarity:
                    continue
                
                # 获取完整的快照数据
                cursor.execute('''
                    SELECT id, ticker, date, total_contracts, calls_count, puts_count,
                           strike_min, strike_max, avg_strike, timestamp
                    FROM options_snapshots
                    WHERE id = ?
                ''', (snapshot_id,))
                
                snapshot_row = cursor.fetchone()
                
                if snapshot_row:
                    # 解析数据
                    cmp_total = snapshot_row[3]
                    cmp_calls = snapshot_row[4]
                    cmp_puts = snapshot_row[5]
                    cmp_strike_min = snapshot_row[6]
                    cmp_strike_max = snapshot_row[7]
                    cmp_avg_strike = snapshot_row[8]
                    cmp_timestamp = snapshot_row[9]
                    
                    # 计算比率
                    ref_ratio = ref_calls / ref_puts if ref_puts > 0 else 0
                    cmp_ratio = cmp_calls / cmp_puts if cmp_puts > 0 else 0
                    
                    anomalies.append({
                        "date": snapshot_date,
                        "timestamp": cmp_timestamp,
                        "similarity_score": round(similarity_score, 4),
                        "distance": round(distance, 4),
                        "anomaly_level": "High" if similarity_score < 0.7 else "Medium" if similarity_score < 0.85 else "Low",
                        "metrics": {
                            "total_contracts": cmp_total,
                            "calls_count": cmp_calls,
                            "puts_count": cmp_puts,
                            "call_put_ratio": round(cmp_ratio, 2) if cmp_puts > 0 else None,
                            "strike_range": f"${cmp_strike_min:.2f} - ${cmp_strike_max:.2f}",
                            "avg_strike": f"${cmp_avg_strike:.2f}"
                        },
                        "changes_from_reference": {
                            "total_contracts_change": cmp_total - ref_total,
                            "calls_change": cmp_calls - ref_calls,
                            "puts_change": cmp_puts - ref_puts,
                            "call_put_ratio_change": round(cmp_ratio - ref_ratio, 2),
                            "avg_strike_change": round(cmp_avg_strike - ref_avg_strike, 2)
                        }
                    })
        
        conn.close()
        
        # 按相似度从低到高排序（相似度越低 = 异动越大）
        anomalies.sort(key=lambda x: x['similarity_score'])
        
        # 返回前 N 个最大异动
        return anomalies[:max_results]
        
    except Exception as e:
        print(f"Error detecting anomalies: {e}")
        import traceback
        traceback.print_exc()
        return [{"error": f"Anomaly detection failed: {str(e)}"}]

# ==================== 初始化 ====================

# 在模块加载时初始化数据库
init_sqlite_db()

if __name__ == "__main__":
    print("RAG Knowledge Base initialized")
    print(f"ChromaDB path: {CHROMA_DB_PATH}")
    print(f"SQLite path: {SQLITE_DB_PATH}")

