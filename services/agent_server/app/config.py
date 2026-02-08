from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tool_server_url: str = Field(default="http://localhost:8001", alias="TOOL_SERVER_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


settings = Settings()
