from functools import lru_cache

from core import get_settings
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

DEFAULT_TASK_EMAIL = "admin@gmail.com"


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.database_url, future=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Session:
    return get_session_factory()()


def _ensure_tasks_email_column(engine: Engine) -> None:
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("tasks")}

    with engine.begin() as connection:
        if "email" not in column_names:
            if engine.dialect.name == "sqlite":
                connection.execute(
                    text(
                        "ALTER TABLE tasks "
                        "ADD COLUMN email VARCHAR(320) NOT NULL "
                        f"DEFAULT '{DEFAULT_TASK_EMAIL}'"
                    )
                )
            else:
                connection.execute(text("ALTER TABLE tasks ADD COLUMN email VARCHAR(320)"))

        connection.execute(
            text("UPDATE tasks SET email = :default_email WHERE email IS NULL OR email = ''"),
            {"default_email": DEFAULT_TASK_EMAIL},
        )

        if engine.dialect.name != "sqlite":
            connection.execute(text("ALTER TABLE tasks ALTER COLUMN email SET NOT NULL"))


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _ensure_tasks_email_column(engine)
