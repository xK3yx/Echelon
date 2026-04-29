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
    # Resume upload (Phase 3)
    max_upload_size_mb: float = 5.0
    resume_confidence_threshold: float = 0.4
    # Course recommendations (Phase 5) — optional; features degrade gracefully if unset
    youtube_api_key: str = ""
    tavily_api_key: str = ""
    course_cache_ttl_days: int = 7
    # Deployment (Phase 11) — production frontend URL, added to CORS allow-list
    public_base_url: str = ""  # e.g. https://echelon.vercel.app

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
