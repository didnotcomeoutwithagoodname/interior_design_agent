"""集中配置：从环境变量 / .env 读取。"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ---- LLM ----
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")      # openai | deepseek | ollama | offline
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or None         # 兼容 OpenAI 协议的自定义地址
LLM_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or None
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# ---- Embedding / RAG ----
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "hash")  # openai | local | hash
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
TOP_K_FURNITURE = int(os.getenv("TOP_K_FURNITURE", "3"))

# ---- 数据 / 输出 ----
DATA_DIR = BASE_DIR / "data"
FURNITURE_CATALOG = DATA_DIR / "furniture_catalog.json"
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", str(DATA_DIR / "chroma"))
OUTPUT_DIR = BASE_DIR / "output"
