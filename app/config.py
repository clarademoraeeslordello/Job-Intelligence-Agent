from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao tipada da aplicacao, carregada do .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///data/database.sqlite"
    claude_api_key: str = ""
    telegram_token: str = ""

    # Lista de board tokens do Greenhouse (empresas a rastrear), separados por virgula.
    # Ex: "spotify,notion,figma". Vazio ate a lista de empresas ser definida (ver PO backlog).
    greenhouse_board_tokens_raw: str = ""

    @property
    def greenhouse_board_tokens(self) -> list[str]:
        return [t.strip() for t in self.greenhouse_board_tokens_raw.split(",") if t.strip()]


settings = Settings()
