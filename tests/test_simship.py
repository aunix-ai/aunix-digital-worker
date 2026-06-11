from datetime import datetime, timedelta, timezone

from aunix.connectors.simship import SimShip

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def make_sim(tmp_path):
    return SimShip(state_path=tmp_path / "simship.json", now=lambda: NOW)


def test_seeds_three_healthy_pos(tmp_path):
    rows = make_sim(tmp_path).fetch()
    assert len(rows) == 3
    assert all(r["delivery_date"] <= r["expected_date"] for r in rows)
    assert all(NOW - r["last_tracking_update"] < timedelta(hours=48) for r in rows)


def test_slip_delivery_persists_across_instances(tmp_path):
    make_sim(tmp_path).slip_delivery("PO-4567", days=2)
    row = next(r for r in make_sim(tmp_path).fetch() if r["po_number"] == "PO-4567")
    assert row["delivery_date"] > row["expected_date"]


def test_freeze_tracking(tmp_path):
    sim = make_sim(tmp_path)
    sim.freeze_tracking("PO-4567", hours=50)
    row = next(r for r in sim.fetch() if r["po_number"] == "PO-4567")
    assert NOW - row["last_tracking_update"] > timedelta(hours=48)
