"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8005
    log_level: str = "INFO"
    service_secret: str
    environment: str = "dev"
    database_url: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "payment_processor"
    db_username: str = "postgres"
    db_password: str = "postgres"

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"postgresql+asyncpg://{self.db_username}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = {"env_prefix": "", "case_sensitive": False}


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
