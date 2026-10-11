"""Runtime configuration for the Feature 1 local workflow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class DatabaseSettings:
    """PostgreSQL settings. Credentials must come from environment variables."""

    host: str
    port: int
    database: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return (
            "postgresql://"
            f"{quote(self.user, safe='')}:{quote(self.password, safe='')}"
            f"@{self.host}:{self.port}/{quote(self.database, safe='')}"
        )


def database_dsn() -> str:
    """Return DATABASE_URL, or build it for localhost:5432/cloud_project."""
    if value := os.environ.get("DATABASE_URL"):
        return value

    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError(
            "Set DATABASE_URL or POSTGRES_PASSWORD in a local .env/environment; "
            "database credentials must not be committed."
        )
    try:
        port = int(os.environ.get("POSTGRES_PORT", "5432"))
    except ValueError as exc:
        raise RuntimeError("POSTGRES_PORT must be an integer.") from exc

    return DatabaseSettings(
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=port,
        database=os.environ.get("POSTGRES_DB", "cloud_project"),
        user=os.environ.get("POSTGRES_USER", "cloud_project_user"),
        password=password,
    ).dsn
