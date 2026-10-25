"""LangChain LLM 工厂。未配置密钥或指定 offline 时返回 None，走离线设计器。"""
from __future__ import annotations


def get_llm():
    import config

    if config.LLM_PROVIDER.lower() == "offline":
        return None
    if not config.LLM_API_KEY:
        return None

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None

    kwargs = {
        "model": config.LLM_MODEL,
        "api_key": config.LLM_API_KEY,
        "temperature": config.LLM_TEMPERATURE,
    }
    if config.LLM_BASE_URL:
        kwargs["base_url"] = config.LLM_BASE_URL

    return ChatOpenAI(**kwargs)
