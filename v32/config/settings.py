import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import RedisDsn, SecretStr, field_validator, Field, EmailStr
from typing import Dict, Optional

# !!! CONFIGURATION LOCK !!!
UAF_IMMUTABLE_MODELS = {
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

    # API Keys for Chimera Protocol
    OPENAI_API_KEY: Optional[SecretStr] = None
    ANTHROPIC_API_KEY: Optional[SecretStr] = None
    GOOGLE_API_KEY: Optional[SecretStr] = None
    XAI_API_KEY: Optional[SecretStr] = None

    # API Keys for Data Connectors
    NEWS_API_KEY: Optional[SecretStr] = None
    GNEWS_API_KEY: Optional[SecretStr] = None
    DART_API_KEY: Optional[SecretStr] = None
    NASA_EARTHDATA_TOKEN: Optional[SecretStr] = None  # NASA Earthdata token

    # Corporate Identity
    CORPORATE_NAME: str = Field(..., min_length=1)
    CORPORATE_EMAIL: EmailStr = Field(...)

    @field_validator('COMMAND_HUB_SECRET')
    def validate_secret(cls, v):
        if len(v.get_secret_value()) < 32:
            raise ValueError("COMMAND_HUB_SECRET must be at least 32 characters long.")
        return v

    @property
    def USER_AGENT(self) -> str:
        return f"{self.CORPORATE_NAME} ({self.CORPORATE_EMAIL})"

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

try:
    settings = Settings()
except Exception as e:
    print(f"FATAL: Configuration loading failed. Check .env file. Error: {e}")
    # 시스템 실행 중이 아닐 때 (예: 스크립트로 실행 시) 종료 로직
    if __name__ != "__main__":
        import sys
        # app.py에서 import 시에는 exit() 호출을 피해야 할 수 있으나, 설정 실패는 치명적이므로 종료가 타당함.
        # 단, uvicorn 환경에서는 exit(1)이 프로세스를 즉시 종료시킬 수 있음.
        # 실제 운영 환경에서는 로깅 후 예외를 다시 발생시키는 것이 더 적절할 수 있음.
        # 현재는 스크립트 기반 배포이므로 exit(1) 유지.
        sys.exit(1)
