from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    stt_provider: str = "deepgram"
    llm_provider: str = "anthropic"
    tts_provider: str = "cartesia"

    deepgram_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    cartesia_api_key: str = ""
    elevenlabs_api_key: str = ""

    default_language: str = "pt-BR"
    llm_model: str = ""
    tts_voice: str = ""

    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # Web test client: remote access needs this bearer token; without it only loopback is allowed.
    web_api_token: str = ""
    max_sessions: int = 10

    crm_base_url: str = "http://localhost:8002/crm"


settings = Settings()
