from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str = ""
    groq_model_ranking: str = "llama-3.3-70b-versatile"
    # Smaller model used only for pure formatting/extraction steps (faster, cheaper)
    groq_model_extraction: str = "llama-3.1-8b-instant"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
