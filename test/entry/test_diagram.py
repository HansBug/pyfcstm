"""CLI tests for the standalone diagram command."""

from click.testing import CliRunner

from pyfcstm.entry.cli import cli


def test_diagram_cli_json_and_html(tmp_path):
    source = tmp_path / "machine.fcstm"
    source.write_text("state Root;", encoding="utf-8")
    json_path = tmp_path / "machine.json"
    html_path = tmp_path / "machine.html"

    runner = CliRunner()
    result = runner.invoke(cli, ["diagram", "-i", str(source), "-o", str(json_path)])
    assert result.exit_code == 0, result.output
    assert '"kind":"diagram"' in json_path.read_text(encoding="utf-8")

    result = runner.invoke(cli, ["diagram", "-i", str(source), "-o", str(html_path)])
    assert result.exit_code == 0, result.output
    assert "Content-Security-Policy" in html_path.read_text(encoding="utf-8")


def test_diagram_cli_open_rejects_non_html_output(tmp_path):
    source = tmp_path / "machine.fcstm"
    source.write_text("state Root;", encoding="utf-8")
    result = CliRunner().invoke(
        cli,
        ["diagram", "-i", str(source), "-o", str(tmp_path / "result.json"), "--open"],
    )
    assert result.exit_code != 0
    assert "输出路径必须以 .html 或 .htm 结尾" in result.output
