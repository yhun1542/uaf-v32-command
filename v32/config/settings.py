import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import RedisDsn, SecretStr, field_validator
# 중요: Optional Import 추가됨
from typing import Dict, Optional

# !!! CONFIGURATION LOCK !!! (모델 고정 지침 준수)
UAF_IMMUTABLE_MODELS: Dict[str, Dict[str, str]] = {
    'gpt-4o-2024-08-06': {'provider': 'OpenAI'},
    'claude-sonnet-4-5-20250929': {'provider': 'Anthropic'},
    'gemini-2.5-pro': {'provider': 'Google'},
    'grok-4-0709': {'provider': 'xAI'},
}

class Settings(BaseSettings):
    # Core Infrastructure
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"
    COMMAND_HUB_SECRET: SecretStr
    KV_STORE_KEY: str = 'operation_singularity:v32:master_plan_state'
    PUBSUB_CHANNEL: str = 'operation_singularity:v32:events'

    # API Keys for Chimera Protocol (자율 개발 에이전트용)
    OPENAI_API_KEY: Optional[SecretStr] = None
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    GOOGLE_API_KEY: Optional[SecretStr] = None
    XAI_API_KEY: Optional[SecretStr] = None

    # API Keys for Data Connectors (데이터 수집용)
    NEWS_API_KEY: Optional[SecretStr] = None
    # (필요시 추가 데이터 소스 키 정의)

    @field_validator('COMMAND_HUB_SECRET')
    def validate_secret(cls, v):
        if len(v.get_secret_value()) < 32:
            raise ValueError("COMMAND_HUB_SECRET must be at least 32 characters long.")
        return v
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

settings = Settings()
