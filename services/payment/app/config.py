"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Payment Service configuration."""

    port: int = 8001
    log_level: str = "INFO"
    service_secret: str
    environment: str = "dev"

    # Database - can be a full URL or constructed from components
    database_url: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "payment_processor"
    db_username: str = "postgres"
    db_password: str = "postgres"

    # Service URLs
    fraud_service_url: str = "http://localhost:8004"
    routing_service_url: str = "http://localhost:8003"
    merchant_service_url: str = "http://localhost:8002"
    analytics_service_url: str = "http://localhost:8005"

    # Payment simulation
    success_rate: float = 0.85

    @property
    def effective_database_url(self) -> str:
        """Get the database URL, constructing from components if not provided."""
        if self.database_url:
            return self.database_url
        return f"postgresql+asyncpg://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = {"env_prefix": "", "case_sensitive": False}


def get_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings()  # type: ignore[call-arg]
