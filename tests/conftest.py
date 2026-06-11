import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aunix.models import Base


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        yield s
