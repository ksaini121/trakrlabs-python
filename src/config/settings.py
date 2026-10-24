from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    app_name: str = "TrakrLabs"
    app_description: str = "TrakrLabs is an ai enabled user story prioritization tool"

    github_client_id: str
    github_client_secret: str
    github_base_url: str = "https://api.github.com"
    github_access_token_url: str = "https://github.com/login/oauth/access_token"
    github_authorize_url: str = "https://github.com/login/oauth/authorize"

    secret_key: str
    env: Literal["dev", "prod"] = "dev"
    frontend_url: str

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "trakrlabs"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    @property
    def is_production(self) -> bool:
        return self.env == "prod"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{quote(self.postgres_user, safe='')}:{quote(self.postgres_password, safe='')}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )



settings = Settings()