from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    toss_secret_key: str = Field(alias="TOSS_SECRET_KEY")
    toss_client_key: str = Field(alias="TOSS_CLIENT_KEY")
    toss_api_base_url: str = Field(
        default="https://api.tosspayments.com",
        alias="TOSS_API_BASE_URL",
    )
    frontend_success_url: str = Field(alias="FRONTEND_SUCCESS_URL")
    frontend_fail_url: str = Field(alias="FRONTEND_FAIL_URL")
    backend_cors_origins_raw: str = Field(
        default="http://localhost:5173",
        alias="BACKEND_CORS_ORIGINS",
    )
    store_path: Path = Field(default=Path("./data/billing_store.json"), alias="STORE_PATH")
    payment_store_path: Path = Field(
        default=Path("./data/payment_store.json"),
        alias="PAYMENT_STORE_PATH",
    )
    toss_test_code: str | None = Field(default=None, alias="TOSS_TEST_CODE")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_cors_origins(settings: Settings) -> list[str]:
    return [origin.strip() for origin in settings.backend_cors_origins_raw.split(",") if origin.strip()]
