from pydantic_settings import BaseSettings
from typing import Optional
import json
import os
import logging

logger = logging.getLogger(__name__)

AI_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".ai_config.json")


class Settings(BaseSettings):
    app_name: str = "LinerDT"
    debug: bool = False

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    sim_default_speed: float = 1.0
    sim_max_speed: float = 100.0

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"

    aisstream_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def load_ai_config():
    """从本地文件加载 AI 配置到 settings."""
    if not os.path.exists(AI_CONFIG_FILE):
        return
    try:
        with open(AI_CONFIG_FILE, "r") as f:
            data = json.load(f)
        if data.get("api_key"):
            settings.openai_api_key = data["api_key"]
        if data.get("base_url"):
            settings.openai_base_url = data["base_url"]
        if data.get("model"):
            settings.openai_model = data["model"]
        logger.info("已从 %s 加载 AI 配置", AI_CONFIG_FILE)
    except Exception as e:
        logger.warning("加载 AI 配置失败: %s", e)


def save_ai_config():
    """将当前 AI 配置保存到本地文件."""
    try:
        data = {
            "api_key": settings.openai_api_key,
            "base_url": settings.openai_base_url,
            "model": settings.openai_model,
        }
        with open(AI_CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("AI 配置已保存到 %s", AI_CONFIG_FILE)
    except Exception as e:
        logger.error("保存 AI 配置失败: %s", e)
