from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_app_id: str = ""
    github_private_key_path: str = ""
    github_webhook_secret: str = ""

    github_api_url: str = "https://api.github.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()