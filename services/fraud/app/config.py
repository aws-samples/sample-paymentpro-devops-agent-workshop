"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Fraud Service configuration."""

    port: int = 8004
    log_level: str = "INFO"
    service_secret: str
    environment: str = "dev"
    metrics_enabled: bool = True
    metrics_namespace: str = "PaymentProcessor/FraudService"

    model_config = {"env_prefix": "", "case_sensitive": False}


def get_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings()  # type: ignore[call-arg]
