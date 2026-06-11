from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    pinecone_api_key: str
    pinecone_index_name: str
    nebius_api_key: str
    pinecone_embedding_model: str = "llama-text-embed-v2"
    pinecone_embedding_dimension: int = 1024
    nebius_base_url: str = "https://api.studio.nebius.com/v1/"
    deepseek_model: str = "deepseek-ai/DeepSeek-V3.2-fast"
    qwen_model: str = "Qwen/Qwen3-32B"


def get_settings() -> Settings:
    settings = Settings(
        pinecone_api_key=os.getenv("PINECONE_API_KEY", ""),
        pinecone_index_name=os.getenv("PINECONE_INDEX_NAME", ""),
        pinecone_embedding_model=os.getenv(
            "PINECONE_EMBEDDING_MODEL", "llama-text-embed-v2"
        ),
        pinecone_embedding_dimension=int(os.getenv("PINECONE_EMBEDDING_DIMENSION", "1024")),
        nebius_api_key=os.getenv("NEBIUS_API_KEY", ""),
        nebius_base_url=os.getenv(
            "NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/"
        ),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3.2-fast"),
        qwen_model=os.getenv("QWEN_MODEL", "Qwen/Qwen3-32B"),
    )

    missing = [
        name
        for name, value in {
            "PINECONE_API_KEY": settings.pinecone_api_key,
            "PINECONE_INDEX_NAME": settings.pinecone_index_name,
            "PINECONE_EMBEDDING_MODEL": settings.pinecone_embedding_model,
            "NEBIUS_API_KEY": settings.nebius_api_key,
            "NEBIUS_BASE_URL": settings.nebius_base_url,
            "DEEPSEEK_MODEL": settings.deepseek_model,
            "QWEN_MODEL": settings.qwen_model,
        }.items()
        if not value or value.startswith("replace-with")
    ]
    if missing:
        raise ValueError(f"Missing required environment values: {', '.join(missing)}")

    return settings
