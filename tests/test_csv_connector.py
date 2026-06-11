from aunix.connectors.csv_source import CsvConnector


def test_reads_rows_with_numeric_coercion(tmp_path):
    p = tmp_path / "leads.csv"
    p.write_text(
        "lead,deal_size,stage\n"
        "Acme,2500000,negotiation\n"
        "Globex,90000,intro\n"
    )
    rows = CsvConnector(path=p).fetch()
    assert rows == [
        {"lead": "Acme", "deal_size": 2500000.0, "stage": "negotiation"},
        {"lead": "Globex", "deal_size": 90000.0, "stage": "intro"},
    ]
