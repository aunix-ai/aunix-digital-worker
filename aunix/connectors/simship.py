"""Simulated shipment/PO service: JSON-file-backed so demo scenarios persist
across processes, with mutation helpers to trigger delays on demand."""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


class SimShip:
    source_id = "simship"

    def __init__(self, state_path: Path, now: Callable[[], datetime] = _default_now):
        self.state_path = Path(state_path)
        self.now = now
        if not self.state_path.exists():
            self._write(self._seed())

    def fetch(self) -> list[dict]:
        rows = []
        for po in self._read():
            row = dict(po)
            row["last_tracking_update"] = datetime.fromisoformat(po["last_tracking_update"])
            rows.append(row)
        return rows

    def slip_delivery(self, po_number: str, days: int) -> None:
        def slip(po: dict) -> None:
            new_date = date.fromisoformat(po["delivery_date"]) + timedelta(days=days)
            po["delivery_date"] = new_date.isoformat()

        self._mutate(po_number, slip)

    def freeze_tracking(self, po_number: str, hours: int) -> None:
        def freeze(po: dict) -> None:
            po["last_tracking_update"] = (self.now() - timedelta(hours=hours)).isoformat()

        self._mutate(po_number, freeze)

    def _seed(self) -> list[dict]:
        today = self.now().date()

        def po(num: str, supplier: str, days_out: int, priority: str) -> dict:
            return {
                "po_number": num,
                "supplier": supplier,
                "expected_date": (today + timedelta(days=days_out)).isoformat(),
                "delivery_date": (today + timedelta(days=days_out)).isoformat(),
                "last_tracking_update": self.now().isoformat(),
                "priority": priority,
                "status": "in_transit",
            }

        return [
            po("PO-4567", "Acme Components", 10, "high"),
            po("PO-4568", "Globex Metals", 14, "medium"),
            po("PO-4569", "Initech Plastics", 7, "low"),
        ]

    def _read(self) -> list[dict]:
        return json.loads(self.state_path.read_text())

    def _write(self, pos: list[dict]) -> None:
        self.state_path.write_text(json.dumps(pos, indent=2))

    def _mutate(self, po_number: str, fn: Callable[[dict], None]) -> None:
        pos = self._read()
        for po in pos:
            if po["po_number"] == po_number:
                fn(po)
        self._write(pos)
