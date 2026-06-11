"""Connector protocol: every data source yields a list of plain-dict rows."""
from typing import Protocol


class Connector(Protocol):
    source_id: str

    def fetch(self) -> list[dict]: ...
