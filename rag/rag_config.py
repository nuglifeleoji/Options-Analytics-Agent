"""
RAG Knowledge Base Configuration
配置文件：数据库路径、Embedding设置、存储策略等
"""
import os
from pathlib import Path

# ==================== 路径配置 ====================

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# ChromaDB 路径
CHROMA_DB_PATH = str(DATA_DIR / "chroma_db")

# SQLite 数据库路径
SQLITE_DB_PATH = str(DATA_DIR / "options.db")

# Embedding 缓存路径
EMBEDDINGS_CACHE_PATH = str(DATA_DIR / "embeddings_cache")

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "chroma_db").mkdir(exist_ok=True)
(DATA_DIR / "embeddings_cache").mkdir(exist_ok=True)

# ==================== Embedding 配置 ====================

# Embedding 提供商
EMBEDDING_PROVIDER = "openai"  # 用户选择：OpenAI

# OpenAI Embedding 配置
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small 的维度

# API Key (从环境变量获取)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ==================== ChromaDB 配置 ====================

# Collection 名称
CHROMA_COLLECTION_NAME = "options_knowledge_base"

# 距离度量方式
DISTANCE_METRIC = "cosine"  # cosine, l2, ip

# ==================== 数据存储配置 ====================

# 数据保留策略
DATA_RETENTION_POLICY = "keep_all"  # 用户选择：保留所有数据

# 最大存储条目数（如果不是 keep_all）
MAX_SNAPSHOTS = None  # None 表示无限制

# 自动清理旧数据（天数）
AUTO_CLEANUP_DAYS = None  # None 表示不自动清理

# ==================== 检索配置 ====================

# 默认检索数量
DEFAULT_SEARCH_LIMIT = 5

# 最大检索数量
MAX_SEARCH_LIMIT = 50

# 相似度阈值（0-1，越高越严格）
SIMILARITY_THRESHOLD = 0.7

# ==================== 元数据配置 ====================

# 需要提取的元数据字段
METADATA_FIELDS = [
    "ticker",
    "date",
    "timestamp",
    "total_contracts",
    "calls_count",
    "puts_count",
    "strike_range_min",
    "strike_range_max",
    "avg_strike",
    "data_source"
]

# ==================== 性能配置 ====================

# 批量处理大小
BATCH_SIZE = 100

# 启用缓存
ENABLE_CACHE = True

# 缓存过期时间（秒）
CACHE_EXPIRY = 3600  # 1小时

# ==================== 日志配置 ====================

# 日志级别
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# 日志文件路径
LOG_FILE = str(DATA_DIR / "rag.log")

# ==================== 验证配置 ====================

def validate_config():
    """验证配置是否正确"""
    errors = []
    
    # 检查 API Key
    if not OPENAI_API_KEY:
        errors.append("⚠️ OPENAI_API_KEY not found in environment variables")
    
    # 检查路径
    if not DATA_DIR.exists():
        errors.append(f"⚠️ Data directory not found: {DATA_DIR}")
    
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  {error}")
        return False
    
    return True

def print_config():
    """打印当前配置"""
    print("="*70)
    print("RAG Knowledge Base Configuration")
    print("="*70)
    print(f"\n📁 Paths:")
    print(f"  • ChromaDB: {CHROMA_DB_PATH}")
    print(f"  • SQLite: {SQLITE_DB_PATH}")
    print(f"  • Cache: {EMBEDDINGS_CACHE_PATH}")
    
    print(f"\n🤖 Embedding:")
    print(f"  • Provider: {EMBEDDING_PROVIDER}")
    print(f"  • Model: {OPENAI_EMBEDDING_MODEL}")
    print(f"  • Dimensions: {OPENAI_EMBEDDING_DIMENSIONS}")
    print(f"  • API Key: {'✅ Set' if OPENAI_API_KEY else '❌ Not Set'}")
    
    print(f"\n💾 Storage:")
    print(f"  • Collection: {CHROMA_COLLECTION_NAME}")
    print(f"  • Retention: {DATA_RETENTION_POLICY}")
    print(f"  • Distance: {DISTANCE_METRIC}")
    
    print(f"\n🔍 Retrieval:")
    print(f"  • Default limit: {DEFAULT_SEARCH_LIMIT}")
    print(f"  • Max limit: {MAX_SEARCH_LIMIT}")
    print(f"  • Similarity threshold: {SIMILARITY_THRESHOLD}")
    
    print("="*70)

if __name__ == "__main__":
    # 验证并打印配置
    if validate_config():
        print("✅ Configuration is valid\n")
        print_config()
    else:
        print("\n❌ Configuration has errors!")

