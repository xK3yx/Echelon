from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    groq_api_key: str = ""
    groq_model_ranking: str = "llama-3.3-70b-versatile"
    # Smaller model used only for pure formatting/extraction steps (faster, cheaper)
    groq_model_extraction: str = "llama-3.1-8b-instant"
    debug: bool = False
    # Single shared token for admin endpoints. Empty string = admin features disabled.
    admin_token: str = ""
    # Stage 2.5: if the top rule-based score falls below this threshold, the
    # LLM proposer is triggered (when allow_proposed=True in the request).
    propose_threshold: float = 0.4

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
