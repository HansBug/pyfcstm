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
    assert "--open requires an .html or .htm output path" in result.output


def test_diagram_cli_help_is_english_and_does_not_leak_rst():
    result = CliRunner().invoke(cli, ["diagram", "--help"])
    assert result.exit_code == 0, result.output
    assert (
        "Generate portable JSON or a standalone HTML diagram viewer." in result.output
    )
    assert "Input FCSTM file." in result.output
    assert ":param" not in result.output
    assert "生成" not in result.output


def test_diagram_cli_open_rejects_non_html_format(tmp_path):
    source = tmp_path / "machine.fcstm"
    source.write_text("state Root;", encoding="utf-8")
    result = CliRunner().invoke(
        cli,
        ["diagram", "-i", str(source), "--format", "json", "--open"],
    )
    assert result.exit_code != 0
    assert "--open requires HTML output" in result.output


def test_diagram_cli_reports_bad_input_without_a_traceback(tmp_path):
    """A typo in the DSL is the most common way this command fails.

    Letting the parser's exception escape buried its own message — which
    already names the line and column — under an unrelated Python stack.
    """
    runner = CliRunner()

    unparsable = tmp_path / "broken.fcstm"
    unparsable.write_text("state Root {\n", encoding="utf-8")
    result = runner.invoke(
        cli, ["diagram", "-i", str(unparsable), "-o", str(tmp_path / "out.json")]
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Failed to parse input DSL file" in result.output
    assert "line 2" in result.output

    invalid = tmp_path / "missing-import.fcstm"
    invalid.write_text(
        'state Root { import "./absent.fcstm" as X; [*] -> X; }\n', encoding="utf-8"
    )
    result = runner.invoke(
        cli, ["diagram", "-i", str(invalid), "-o", str(tmp_path / "out2.json")]
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Invalid state machine model in" in result.output

    # A well-formed model is unaffected.
    good = tmp_path / "good.fcstm"
    good.write_text("state Root { state A; [*] -> A; }\n", encoding="utf-8")
    result = runner.invoke(
        cli, ["diagram", "-i", str(good), "-o", str(tmp_path / "out3.json")]
    )
    assert result.exit_code == 0
