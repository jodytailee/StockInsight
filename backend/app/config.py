from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./stockinsight.db"
    frontend_url: str = "http://localhost:5173"
    finnhub_api_key: str = ""
    anthropic_api_key: str = ""
    resend_api_key: str = ""
    resend_from_email: str = "StockInsight <onboarding@resend.dev>"
    notification_email_to: str = "jodytailee@gmail.com"

    class Config:
        env_file = ".env"


settings = Settings()
