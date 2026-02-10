from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_url: str

    @staticmethod
    def from_env() -> "Settings":
        secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
        database_url = os.environ.get("DATABASE_URL", "sqlite:///instance/lancenotas.sqlite3")
        return Settings(secret_key=secret_key, database_url=database_url)

