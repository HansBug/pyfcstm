"""CLI tests for the standalone diagram command."""

import os
import stat
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyfcstm.entry.cli import cli

# Without this the whole file is deselected by `pytest -m unittest`, which is
# the only Python path CI runs, so every test here would be dead weight.
pytestmark = pytest.mark.unittest


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


@pytest.mark.skipif(os.name == "nt", reason="POSIX modes")
@pytest.mark.parametrize("name", ["machine.json", "machine.html"])
def test_diagram_cli_can_overwrite_its_own_output_under_a_write_clearing_umask(
    name, tmp_path
):
    # `-o` used to carry Click's `writable=True`, which is `os.access(W_OK)` --
    # the criterion the library dropped precisely because it cannot tell a file
    # the user protected from one whose write bit a umask cleared. Under a umask
    # like this the first run produced a 0444 file and the second was refused at
    # argument parsing, so the CLI kept the one-shot behaviour after the library
    # had lost it, and the two disagreed about the same file.
    source = tmp_path / "machine.fcstm"
    source.write_text("state Root;", encoding="utf-8")
    target = tmp_path / name

    runner = CliRunner()
    previous = os.umask(0o222)
    try:
        first = runner.invoke(cli, ["diagram", "-i", str(source), "-o", str(target)])
        assert first.exit_code == 0, first.output
        assert stat.S_IMODE(target.stat().st_mode) == 0o444, "the umask cleared it"
        second = runner.invoke(cli, ["diagram", "-i", str(source), "-o", str(target)])
    finally:
        os.umask(previous)
    assert second.exit_code == 0, second.output
    assert stat.S_IMODE(target.stat().st_mode) == 0o444, "and it stays cleared"


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


def test_diagram_cli_reports_a_bad_output_path_without_a_traceback(tmp_path):
    """The write side had the same defect the input side did.

    ``_validate_write_target`` produces a message naming the path and the real
    problem, and letting the exception escape buried it in a stack.
    """
    runner = CliRunner()
    source = tmp_path / "machine.fcstm"
    source.write_text("state Root { state A; [*] -> A; }\n", encoding="utf-8")
    existing = tmp_path / "already.json"
    existing.write_text("{}", encoding="utf-8")

    for target in (
        tmp_path / "absent" / "out.json",  # parent directory does not exist
        existing / "out.json",  # parent is a file
    ):
        result = runner.invoke(
            cli, ["diagram", "-i", str(source), "-o", str(target), "--format", "json"]
        )
        assert result.exit_code == 1, target
        assert "Traceback" not in result.output, target
        assert "Failed to write" in result.output, target

    # A directory destination is rejected earlier, by click's own -o validation,
    # which says so more directly than the writer could.
    result = runner.invoke(
        cli, ["diagram", "-i", str(source), "-o", str(tmp_path), "--format", "json"]
    )
    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert "is a directory" in result.output

    result = runner.invoke(
        cli, ["diagram", "-i", str(source), "-o", str(tmp_path / "fine.json")]
    )
    assert result.exit_code == 0


def test_diagram_cli_open_failure_names_only_a_document_that_survives(tmp_path):
    # A failed launch used to print the path of a second temporary copy, which
    # the exit hook then removed: the user was handed a ~30 MB file that was
    # already gone. With -o the document is not temporary and naming it is
    # correct; without -o there is nothing to name.
    source = tmp_path / "machine.fcstm"
    source.write_text("state Root;", encoding="utf-8")
    kept = tmp_path / "kept.html"
    env = {"PYFCSTM_BROWSER": str(tmp_path / "no-such-browser")}

    result = CliRunner().invoke(
        cli, ["diagram", "-i", str(source), "-o", str(kept), "--open"], env=env
    )
    assert result.exit_code != 0
    assert str(kept) in result.output
    assert kept.is_file(), "an explicit output path must survive a failed launch"

    result = CliRunner().invoke(cli, ["diagram", "-i", str(source), "--open"], env=env)
    assert result.exit_code != 0
    assert "-o PATH" in result.output
    for line in result.output.splitlines():
        for token in line.split():
            candidate = Path(token.rstrip(";,"))
            if candidate.name.startswith("pyfcstm-diagram-"):
                raise AssertionError(
                    "named a temporary viewer that is removed at exit: %s" % token
                )
