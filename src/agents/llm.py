import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()


def build_chat_model(temperature: float = 0) -> ChatOpenAI:
    nebius_api_key = os.getenv("NEBIUS_API_KEY", "")
    if nebius_api_key:
        return ChatOpenAI(
            api_key=nebius_api_key,
            base_url=os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/"),
            model=os.getenv("QWEN_MODEL", "Qwen/Qwen3-32B"),
            temperature=temperature,
        )

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if openai_api_key:
        return ChatOpenAI(
            api_key=openai_api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=temperature,
        )

    raise RuntimeError("Set NEBIUS_API_KEY or OPENAI_API_KEY before running GrantPulse agents.")
