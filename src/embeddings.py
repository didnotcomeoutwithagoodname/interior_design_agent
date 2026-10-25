"""可插拔 Embedding，兼容 LangChain Embeddings 接口。

三种实现：
- openai : 真实语义向量（需 OPENAI_API_KEY）
- local  : HuggingFace sentence-transformers 多语言模型（首次运行需下载，较重）
- hash   : 字符 n-gram 哈希，零依赖、离线可用，用于演示/测试
"""
from __future__ import annotations

import hashlib
import math
from typing import List

from langchain_core.embeddings import Embeddings

DIM = 256


def _hash_embedding(text: str, dim: int = DIM) -> List[float]:
    """把文本映射为 dim 维归一化向量。字符 unigram + bigram 哈希后带符号累加。"""
    vec = [0.0] * dim
    s = text.lower()
    tokens = list(s) + [s[i:i + 2] for i in range(len(s) - 1)]
    for t in tokens:
        h = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashEmbeddings(Embeddings):
    """离线哈希 embedding，向量归一化后与余弦/L2 检索都能配合。"""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [_hash_embedding(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return _hash_embedding(text)


class OpenAIImplEmbeddings(Embeddings):
    """包装 langchain-openai 的 OpenAIEmbeddings。"""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        from langchain_openai import OpenAIEmbeddings
        kwargs = {"model": model, "api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._impl = OpenAIEmbeddings(**kwargs)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._impl.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._impl.embed_query(text)


def get_embeddings() -> Embeddings:
    import config

    provider = config.EMBEDDING_PROVIDER.lower()
    if provider == "openai":
        if not config.LLM_API_KEY:
            raise RuntimeError("EMBEDDING_PROVIDER=openai 需要 OPENAI_API_KEY")
        return OpenAIImplEmbeddings(config.LLM_API_KEY, config.EMBEDDING_MODEL, config.LLM_BASE_URL)
    if provider == "local":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return HashEmbeddings()
