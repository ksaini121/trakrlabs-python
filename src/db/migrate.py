from pathlib import Path

from config.settings import settings
from yoyo import get_backend, read_migrations

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def migrate() -> None:
    backend = get_backend(
        settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    )
    migrations = read_migrations(str(MIGRATIONS_DIR))
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


def rollback() -> None:
    """Roll back the most recently applied migration."""
    backend = get_backend(
        settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    )
    migrations = read_migrations(str(MIGRATIONS_DIR))
    with backend.lock():
        applied = backend.to_rollback(migrations)
        backend.rollback_migrations(applied[:1])


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["down"]:
        rollback()
    else:
        migrate()
