"""CLI tests for the standalone diagram command."""

import json
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


def test_diagram_cli_open_prints_no_path_it_has_already_removed(tmp_path, monkeypatch):
    # Every other mode prints a path that can be opened now. Without -o there is
    # nothing left to print: the window has closed and the document is gone, so a
    # path here would be the only ghost -- and `p=$(pyfcstm diagram -i x --open)`
    # would collect it.
    import pyfcstm.diagram.api as diagram_api

    source = tmp_path / "machine.fcstm"
    source.write_text("state Root;", encoding="utf-8")
    monkeypatch.setattr(diagram_api, "_open_standalone_window", lambda *_: None)

    result = CliRunner().invoke(cli, ["diagram", "-i", str(source), "--open"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "", "a removed document has no path to print"

    named = tmp_path / "kept.html"
    result = CliRunner().invoke(
        cli, ["diagram", "-i", str(source), "-o", str(named), "--open"]
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip() == str(named)
    assert named.is_file()


def test_diagram_cli_help_is_english_and_does_not_leak_rst():
    result = CliRunner().invoke(cli, ["diagram", "--help"])
    assert result.exit_code == 0, result.output
    assert (
        "Generate portable JSON, a standalone HTML viewer, or an SVG/PNG/PDF "
        "export." in result.output
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


@pytest.mark.unittest
class TestDiagramCommandExports:
    """
    Cover the export formats the command gained alongside JSON and HTML.

    The optional rendering runtime may be absent, and both outcomes are part of
    the contract: a file appears, or the failure names the dependency. Asserting
    only "exit code 0" would pass in an environment where nothing was rendered.
    """

    @pytest.mark.parametrize("suffix", ["svg", "png", "pdf"])
    def test_an_export_lands_on_disk_or_names_its_missing_dependency(
        self, tmp_path, suffix
    ):
        source = tmp_path / "machine.fcstm"
        source.write_text("state Root { state A; [*] -> A; }", encoding="utf-8")
        target = tmp_path / ("machine." + suffix)
        result = CliRunner().invoke(
            cli, ["diagram", "-i", str(source), "-o", str(target)]
        )
        if result.exit_code == 0:
            assert target.stat().st_size > 0
            assert str(target) in result.output
        else:
            assert "pyfcstm[viz]" in result.output

    def test_a_scale_is_refused_for_a_format_that_has_none(self, tmp_path):
        source = tmp_path / "machine.fcstm"
        source.write_text("state Root { state A; [*] -> A; }", encoding="utf-8")
        result = CliRunner().invoke(
            cli,
            [
                "diagram",
                "-i",
                str(source),
                "-o",
                str(tmp_path / "machine.svg"),
                "--scale",
                "2",
            ],
        )
        assert result.exit_code != 0
        assert "--scale is only supported for PNG output" in result.output

    def test_a_scale_above_the_ceiling_is_a_usage_error(self, tmp_path):
        source = tmp_path / "machine.fcstm"
        source.write_text("state Root { state A; [*] -> A; }", encoding="utf-8")
        result = CliRunner().invoke(
            cli,
            [
                "diagram",
                "-i",
                str(source),
                "-o",
                str(tmp_path / "machine.png"),
                "--scale",
                "5",
            ],
        )
        # A caller mistake, so it must be reported as one rather than as a
        # rendering failure or a traceback.
        assert result.exit_code != 0
        assert "4" in result.output
        assert "Traceback" not in result.output

    def test_an_unknown_suffix_lists_every_format_the_command_writes(self, tmp_path):
        source = tmp_path / "machine.fcstm"
        source.write_text("state Root { state A; [*] -> A; }", encoding="utf-8")
        result = CliRunner().invoke(
            cli, ["diagram", "-i", str(source), "-o", str(tmp_path / "machine.tiff")]
        )
        assert result.exit_code != 0
        for name in (".json", ".html", ".svg", ".png", ".pdf"):
            assert name in result.output


def test_diagram_cli_writes_json_to_standard_output(tmp_path):
    """Without ``-o`` the document goes to standard output.

    This is the first form the command's help documents and the one a caller
    pipes into something else, and it had no test: a change that started writing
    a file instead, or printing a summary line alongside the document, would have
    broken every such pipeline without failing anything here.
    """
    runner = CliRunner()
    source = tmp_path / "machine.fcstm"
    source.write_text(
        "state Root { state A; state B; [*] -> A; A -> B; }", encoding="utf-8"
    )

    result = runner.invoke(cli, ["diagram", "-i", str(source)])

    assert result.exit_code == 0, result.output
    # The whole of standard output has to be the document, with nothing around
    # it, or `pyfcstm diagram -i x.fcstm | jq` stops working.
    document = json.loads(result.output)
    assert document["kind"] == "diagram"
    assert document["machineName"] == "Root"
    assert document["summary"]["states"] == 3
    assert [child["id"] for child in document["rootState"]["children"]] == [
        "Root.A",
        "Root.B",
    ]


def test_diagram_cli_refuses_a_non_json_format_with_nowhere_to_write_it(tmp_path):
    """Only JSON can go to standard output, and asking otherwise is a usage error.

    A PNG on a terminal is not what the flag combination asks for. What this
    pins is the outcome, not the order: exit 2 rather than merely non-zero,
    because Click gives a usage error 2 and a failed operation 1, and a shell
    branches on which one it got. Whether the export ran first is not observable
    from here without reaching into the command, so it is not claimed.
    """
    runner = CliRunner()
    source = tmp_path / "machine.fcstm"
    source.write_text("state Root { state A; [*] -> A; }", encoding="utf-8")

    for format_name in ("svg", "png", "pdf", "html"):
        result = runner.invoke(
            cli, ["diagram", "-i", str(source), "--format", format_name]
        )
        # Exit 2, not merely non-zero: a usage error and a failed export are
        # different outcomes, and a shell branches on which one it got.
        assert result.exit_code == 2, (format_name, result.output)
        assert "Traceback" not in result.output
        assert "JSON is the only format" in result.output


def test_diagram_cli_reports_a_binary_input_without_a_traceback(tmp_path):
    """Pointing ``-i`` at the wrong file is an ordinary mistake.

    The bytes of a compiled artefact fit no text encoding, and ``auto_decode``
    raising through the command buried a message about encodings under a Python
    stack about the DSL.
    """
    runner = CliRunner()
    source = tmp_path / "not-a-machine.fcstm"
    # These bytes reach the decode failure because `chardet` declines to commit
    # to an encoding for them. `chardet` is not pinned, and an encoding that
    # accepts every byte would instead make this a parse failure -- so if this
    # test starts failing after a dependency bump, the message will say "Failed
    # to parse" and the premise, not the command, is what moved.
    source.write_bytes(bytes(range(256)) * 8)

    result = runner.invoke(
        cli, ["diagram", "-i", str(source), "-o", str(tmp_path / "out.json")]
    )

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Failed to decode input DSL file" in result.output
    assert "not-a-machine.fcstm" in result.output
