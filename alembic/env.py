import sys
import os
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

# Ensure Alembic can find your app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import config and models
from config.settings import settings  # Pydantic settings with .env already loaded
from config.database import Base      # Contains SQLAlchemy Base

# Load Alembic config
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Pull in the raw DATABASE_URL
raw_url = settings.DATABASE_URL
if not raw_url:
    raise ValueError("DATABASE_URL not set in .env")

# Inject into Alembic config—escape % for ConfigParser’s sake
escaped_url = raw_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", escaped_url)

# Make the raw URL available for actual connections
DATABASE_URL = raw_url

# Attach your model metadata for `--autogenerate`
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=DATABASE_URL,            # use the raw, single-% URL here
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    engine = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
