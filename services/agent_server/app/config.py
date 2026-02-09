from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tool_server_url: str = Field(default="http://localhost:8001", alias="TOOL_SERVER_URL")
    agent_mode: str = Field(default="deterministic", alias="AGENT_MODE")
    llm_model_id: str = Field(default="mistralai/Mistral-7B-Instruct-v0.2", alias="LLM_MODEL_ID")
    llm_adapter_dir: str = Field(default="models/sft_qlora/adapter", alias="LLM_ADAPTER_DIR")
    llm_device: str = Field(default="auto", alias="LLM_DEVICE")
    llm_dtype: str = Field(default="auto", alias="LLM_DTYPE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


settings = Settings()
