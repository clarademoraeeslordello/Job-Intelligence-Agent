from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao tipada da aplicacao, carregada do .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///data/database.sqlite"
    claude_api_key: str = ""
    telegram_token: str = ""


settings = Settings()
