from zomato_analytics import cli


def test_cli_sample_writes_file(tmp_path):
    out = tmp_path / "s.csv"
    assert cli.main(["sample", "--out", str(out), "--rows", "50"]) == 0
    assert out.exists()


def test_cli_run_without_charts(tmp_path):
    src = tmp_path / "s.csv"
    cli.main(["sample", "--out", str(src), "--rows", "600"])
    assert cli.main(["run", "--input", str(src), "--out", str(tmp_path / "o"), "--no-charts"]) == 0
    assert (tmp_path / "o" / "executive_summary.md").exists()
