import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_SUPPORTED_BACKENDS = {"ollama", "anthropic", "openai", "gemini"}


@dataclass
class Config:
    backend: str
    ollama_model: str
    ollama_base_url: str
    anthropic_api_key: str
    openai_api_key: str
    gemini_api_key: str
    profile_dir: Path


def load_config() -> Config:
    backend = os.getenv("AI_BACKEND", "ollama").lower().strip()

    if backend not in _SUPPORTED_BACKENDS:
        raise ValueError(
            f"AI_BACKEND='{backend}' is not supported. "
            f"Choose one of: {', '.join(sorted(_SUPPORTED_BACKENDS))}"
        )

    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    if backend == "anthropic" and not anthropic_key:
        raise ValueError(
            "AI_BACKEND=anthropic requires ANTHROPIC_API_KEY to be set in your .env file."
        )
    if backend == "openai" and not openai_key:
        raise ValueError(
            "AI_BACKEND=openai requires OPENAI_API_KEY to be set in your .env file."
        )
    if backend == "gemini" and not gemini_key:
        raise ValueError(
            "AI_BACKEND=gemini requires GEMINI_API_KEY to be set in your .env file."
        )

    return Config(
        backend=backend,
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        anthropic_api_key=anthropic_key,
        openai_api_key=openai_key,
        gemini_api_key=gemini_key,
        profile_dir=Path.home() / ".kadhaigpt",
    )
