from aunix.demo import run_demo


def test_demo_end_to_end(tmp_path, capsys):
    run_demo(workdir=tmp_path)
    out = capsys.readouterr().out
    assert "PO-4567" in out          # delivery slip alerted
    assert "PO-4568" in out          # stale tracking alerted
    assert "#1: Hooli Platform" in out  # top lead by deal size
    assert out.count("PO-4567") == 1    # no duplicate alert across two runs
