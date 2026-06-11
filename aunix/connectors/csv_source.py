import csv
from pathlib import Path


class CsvConnector:
    source_id = "csv"

    def __init__(self, path: Path):
        self.path = Path(path)

    def fetch(self) -> list[dict]:
        with self.path.open(newline="") as f:
            return [
                {k: _coerce(v) for k, v in row.items()}
                for row in csv.DictReader(f)
            ]


def _coerce(value: str | None) -> float | str | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return value
