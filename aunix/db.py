import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(url: str | None = None) -> Engine:
    return create_engine(url or os.environ.get("DATABASE_URL", "sqlite:///aunix.db"))


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)
