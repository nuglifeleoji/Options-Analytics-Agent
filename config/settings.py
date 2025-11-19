"""
Configuration Settings
Author: Leo Ji

Centralized configuration management for the Financial Options Analysis Agent.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# API Keys
# ============================================================================
class APIKeys:
    """API key management"""
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    @classmethod
    def validate(cls):
        """Validate that required API keys are present"""
        missing = []
        if not cls.POLYGON_API_KEY:
            missing.append("POLYGON_API_KEY")
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        
        if missing:
            raise ValueError(f"Missing required API keys: {', '.join(missing)}")
        
        return True


# ============================================================================
# Model Configuration
# ============================================================================
class ModelConfig:
    """LLM model configuration"""
    # Default model
    MODEL_NAME = "gpt-4o-mini"
    MODEL_PROVIDER = "openai"
    
    # Model parameters
    TEMPERATURE = 0.7
    MAX_TOKENS = None
    
    # Judge model (for evaluation)
    JUDGE_MODEL_NAME = "gpt-4o-mini"
    JUDGE_MODEL_PROVIDER = "openai"


# ============================================================================
# System Limits
# ============================================================================
class Limits:
    """System resource limits"""
    # Context management
    MAX_MESSAGES = 20  # Maximum conversation history messages
    MAX_CONTEXT_TOKENS = 128000  # GPT-4o-mini token limit
    SAFE_CONTEXT_TOKENS = 80000  # Conservative limit
    
    # Data limits
    MAX_OPTIONS_CONTRACTS = 1000  # Maximum contracts per query
    DEFAULT_OPTIONS_LIMIT = 100
    RECOMMENDED_OPTIONS_LIMIT = 500
    
    # API limits
    POLYGON_API_RATE_LIMIT = 5  # Requests per minute (free tier)
    API_TIMEOUT = 30  # Seconds


# ============================================================================
# File Paths
# ============================================================================
class Paths:
    """File and directory paths"""
    # Data directories
    DATA_DIR = "data"
    CHROMA_DB_DIR = os.path.join(DATA_DIR, "chroma_db")
    EMBEDDINGS_CACHE_DIR = os.path.join(DATA_DIR, "embeddings_cache")
    
    # Databases
    CONVERSATION_MEMORY_DB = os.path.join(DATA_DIR, "conversation_memory.db")
    OPTIONS_DB = os.path.join(DATA_DIR, "options.db")
    
    # Output directories
    OUTPUTS_DIR = "outputs"
    CHARTS_DIR = os.path.join(OUTPUTS_DIR, "charts")
    REPORTS_DIR = os.path.join(OUTPUTS_DIR, "reports")
    CSV_DIR = os.path.join(OUTPUTS_DIR, "csv")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        directories = [
            cls.DATA_DIR,
            cls.CHROMA_DB_DIR,
            cls.EMBEDDINGS_CACHE_DIR,
            cls.OUTPUTS_DIR,
            cls.CHARTS_DIR,
            cls.REPORTS_DIR,
            cls.CSV_DIR,
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)


# ============================================================================
# Agent Configuration
# ============================================================================
class AgentConfig:
    """Agent behavior configuration"""
    # Thread ID for conversation tracking
    DEFAULT_THREAD_ID = "1"
    
    # Debug mode
    DEBUG = False
    VERBOSE = True
    
    # Performance monitoring
    ENABLE_PERFORMANCE_MONITORING = True
    ENABLE_TOKEN_TRACKING = True


# ============================================================================
# RAG Configuration
# ============================================================================
class RAGConfig:
    """RAG system configuration"""
    # ChromaDB settings
    COLLECTION_NAME = "options_snapshots"
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSION = 1536
    
    # Search settings
    DEFAULT_SEARCH_LIMIT = 5
    MAX_SEARCH_RESULTS = 20
    MIN_SIMILARITY_THRESHOLD = 0.7
    
    # Anomaly detection
    ANOMALY_DETECTION_ENABLED = True
    ANOMALY_MIN_SIMILARITY = 0.0
    ANOMALY_MAX_RESULTS = 5


# ============================================================================
# Visualization Configuration
# ============================================================================
class VisualizationConfig:
    """Chart and visualization settings"""
    # Matplotlib backend
    MATPLOTLIB_BACKEND = 'Agg'  # Non-interactive
    
    # Default chart settings
    DEFAULT_FIGURE_SIZE = (14, 8)
    DEFAULT_DPI = 100
    
    # Color scheme
    CALL_COLOR = 'green'
    PUT_COLOR = 'red'


# ============================================================================
# Global Settings Object
# ============================================================================
class Settings:
    """Global settings aggregator"""
    api_keys = APIKeys
    model = ModelConfig
    limits = Limits
    paths = Paths
    agent = AgentConfig
    rag = RAGConfig
    visualization = VisualizationConfig
    
    @classmethod
    def initialize(cls):
        """Initialize settings and validate"""
        # Validate API keys
        cls.api_keys.validate()
        
        # Ensure directories exist
        cls.paths.ensure_directories()
        
        # Set matplotlib backend
        import matplotlib
        matplotlib.use(cls.visualization.MATPLOTLIB_BACKEND)
        
        return True


# Create singleton instance
settings = Settings()

# Export convenient aliases
API_KEYS = settings.api_keys
MODEL_CONFIG = settings.model
LIMITS = settings.limits
PATHS = settings.paths
AGENT_CONFIG = settings.agent
RAG_CONFIG = settings.rag
VIZ_CONFIG = settings.visualization

__all__ = [
    'settings',
    'Settings',
    'API_KEYS',
    'MODEL_CONFIG',
    'LIMITS',
    'PATHS',
    'AGENT_CONFIG',
    'RAG_CONFIG',
    'VIZ_CONFIG',
]

