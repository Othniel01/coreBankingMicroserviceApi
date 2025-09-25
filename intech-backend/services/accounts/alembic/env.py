# services/accounts/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import create_engine as sync_create_engine
from alembic import context

from app.models.accounts import Base
from app.core.config import settings

# Alembic Config object
config = context.config

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate'
target_metadata = Base.metadata

# Sync database URL
SYNC_DATABASE_URL = (
    settings.DATABASE_URL_SYNC
)  # make sure this is set in your settings.py


# Offline migration
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection)."""
    context.configure(
        url=SYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# Online migration
def run_migrations_online() -> None:
    """Run migrations in online mode with sync engine."""
    engine = sync_create_engine(SYNC_DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


# Determine mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
