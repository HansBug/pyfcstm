import json
import os
import re
import textwrap
from tempfile import TemporaryDirectory

import pytest
from hbutils.testing import isolated_directory, simulate_entry

from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.base import ClickErrorException
from pyfcstm.diagnostics.inspect_render import INSPECT_LLM_DRAFT_SCHEMA_VERSION
from pyfcstm.entry.inspect import (
    build_inspect_json,
    build_inspect_output,
    resolve_inspect_color_enabled,
)


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
BOX_DRAWING_RE = re.compile(r"[\u2500-\u257f]")


@pytest.fixture()
def inspect_code_file():
    with TemporaryDirectory() as td:
        code_file = os.path.join(td, "inspect_case.fcstm")
        with open(code_file, "w", encoding="utf-8") as f:
            print(
                textwrap.dedent("""
                    def int x = 0;
                    state Root {
                        state Idle;
                        state Running;
                        [*] -> Idle;
                        Idle -> Running : if [x > 0 && x < 0];
                    }
                """).strip(),
                file=f,
            )
        yield code_file


def _run_inspect(*args):
    return simulate_entry(pyfcstmcli, ["pyfcstm", "inspect", *args])


def _json_from_stdout(result):
    return json.loads(result.stdout)


def _has_ansi(text):
    return ANSI_ESCAPE_RE.search(text) is not None


@pytest.mark.unittest
class TestEntryInspect:
    @pytest.mark.parametrize(
        (
            "color_mode",
            "output_format",
            "output_file",
            "stdout_isatty",
            "no_color",
            "term",
            "expected",
        ),
        [
            ("auto", "human", None, True, "", "xterm-256color", True),
            ("auto", "human", None, False, "", "xterm-256color", False),
            ("auto", "human", None, True, "1", "xterm-256color", False),
            ("auto", "human", None, True, "0", "xterm-256color", False),
            ("auto", "human", None, True, "false", "xterm-256color", False),
            ("auto", "human", None, True, "", "dumb", False),
            ("always", "human", None, False, "1", "dumb", True),
            ("never", "human", None, True, "", "xterm-256color", False),
            ("always", "human", "report.txt", True, "", "xterm-256color", False),
            ("always", "json", None, True, "", "xterm-256color", False),
            ("always", "llm-json", None, True, "", "xterm-256color", False),
            ("always", "llm-md", None, True, "", "xterm-256color", False),
        ],
    )
    def test_resolve_inspect_color_enabled_policy(
        self,
        color_mode,
        output_format,
        output_file,
        stdout_isatty,
        no_color,
        term,
        expected,
    ):
        assert (
            resolve_inspect_color_enabled(
                color_mode,
                output_format=output_format,
                output_file=output_file,
                stdout_isatty=stdout_isatty,
                no_color=no_color,
                term=term,
            )
            is expected
        )

    def test_inspect_outputs_default_human_to_stdout(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file)

        assert result.exitcode == 0
        assert "[WARN ] FCSTM Inspect Report" in result.stdout
        assert "status: warning" in result.stdout
        assert "W_DEADLOCK_LEAF" in result.stdout
        assert "-->" in result.stdout
        assert "= source: inspect-static" in result.stdout
        assert "= why:" in result.stdout
        assert "= fix:" in result.stdout
        assert "= do-not:" in result.stdout
        assert not _has_ansi(result.stdout)
        with pytest.raises(json.JSONDecodeError):
            json.loads(result.stdout)

    def test_inspect_human_color_always_outputs_ansi_to_stdout(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--color", "always")

        assert result.exitcode == 0
        assert _has_ansi(result.stdout)
        assert "[WARN ]" in ANSI_ESCAPE_RE.sub("", result.stdout)

    def test_inspect_human_color_never_outputs_plain_text(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--color", "never")

        assert result.exitcode == 0
        assert not _has_ansi(result.stdout)
        assert "[WARN ] FCSTM Inspect Report" in result.stdout

    def test_inspect_human_output_file_stays_plain_even_when_color_always(
        self, inspect_code_file
    ):
        with isolated_directory():
            result = _run_inspect(
                "-i",
                inspect_code_file,
                "--color",
                "always",
                "-o",
                "inspect_report.txt",
            )

            assert result.exitcode == 0
            assert result.stdout == ""
            with open("inspect_report.txt", "r", encoding="utf-8") as f:
                text = f.read()
            assert not _has_ansi(text)
            assert BOX_DRAWING_RE.search(text) is None
            assert "[WARN ] FCSTM Inspect Report" in text

    def test_inspect_format_json_outputs_full_json_to_stdout(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--format", "json")

        assert result.exitcode == 0
        assert not _has_ansi(result.stdout)
        payload = _json_from_stdout(result)
        assert payload["root_state_path"] == "Root"
        assert payload["states"]
        assert payload["transitions"]
        assert "reachability_graph" in payload
        assert "diagnostics" in payload
        assert "W_DEAD_GUARD" not in {
            diagnostic["code"] for diagnostic in payload["diagnostics"]
        }

    def test_inspect_format_llm_json_outputs_draft_packet(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--format", "llm-json")

        assert result.exitcode == 0
        assert not _has_ansi(result.stdout)
        payload = _json_from_stdout(result)
        assert payload["schema_version"] == INSPECT_LLM_DRAFT_SCHEMA_VERSION
        assert payload["schema_status"] == "draft"
        assert payload["status"] == "warning"
        assert payload["diagnostics"]
        assert "source_excerpt" in payload["diagnostics"][0]
        assert "for_llm" not in payload

    def test_inspect_format_llm_md_outputs_draft_markdown(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--format", "llm-md")

        assert result.exitcode == 0
        assert not _has_ansi(result.stdout)
        assert "# FCSTM Inspect Report" in result.stdout
        assert INSPECT_LLM_DRAFT_SCHEMA_VERSION in result.stdout
        assert "Recommended actions" in result.stdout

    def test_inspect_llm_json_can_include_verify_backed_diagnostics(
        self, inspect_code_file
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            "llm-json",
            "--enable-verify",
            "--max-complexity-tier",
            "smt_linear",
            "--smt-timeout-ms",
            "1000",
        )

        assert result.exitcode == 0
        payload = _json_from_stdout(result)
        verify_diagnostics = [
            diagnostic
            for diagnostic in payload["diagnostics"]
            if diagnostic["code"] == "W_DEAD_GUARD"
        ]
        assert verify_diagnostics
        assert verify_diagnostics[0]["source"] == "verify-backed"

    @pytest.mark.parametrize("output_format", ["json", "llm-json", "llm-md"])
    def test_inspect_machine_formats_ignore_color_always(
        self, inspect_code_file, output_format
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            output_format,
            "--color",
            "always",
        )

        assert result.exitcode == 0
        assert not _has_ansi(result.stdout)
        if output_format != "llm-md":
            json.loads(result.stdout)

    @pytest.mark.parametrize("output_format", ["human", "llm-md"])
    def test_inspect_verify_combines_with_text_formats(
        self, inspect_code_file, output_format
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            output_format,
            "--enable-verify",
            "--max-complexity-tier",
            "smt_linear",
            "--smt-timeout-ms",
            "1000",
        )

        assert result.exitcode == 0
        assert "W_DEAD_GUARD" in result.stdout
        assert "verify-backed" in result.stdout

    def test_inspect_verify_human_checker_style_marks_verify_source(
        self, inspect_code_file
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            "human",
            "--enable-verify",
            "--max-complexity-tier",
            "smt_linear",
            "--smt-timeout-ms",
            "1000",
        )

        assert result.exitcode == 0
        assert "[WARN ] W_DEAD_GUARD" in result.stdout
        assert "= source: verify-backed" in result.stdout
        assert "= fix:" in result.stdout

    def test_build_inspect_output_json_matches_build_inspect_json(
        self, inspect_code_file
    ):
        assert build_inspect_output(
            inspect_code_file,
            output_format="json",
        ) == build_inspect_json(inspect_code_file)

    def test_inspect_enable_verify_exposes_verify_diagnostics(self, inspect_code_file):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            "json",
            "--enable-verify",
            "--max-complexity-tier",
            "smt_linear",
            "--smt-timeout-ms",
            "1000",
        )

        assert result.exitcode == 0
        payload = _json_from_stdout(result)
        assert "W_DEAD_GUARD" in {
            diagnostic["code"] for diagnostic in payload["diagnostics"]
        }

    def test_inspect_help_documents_formats_and_zero_smt_timeout(self):
        result = _run_inspect("--help")

        assert result.exitcode == 0
        assert "--format [human|json|llm-json|llm-md]" in result.stdout
        assert "--color [auto|always|never]" in result.stdout
        assert "default: human" in result.stdout
        assert "default: auto" in result.stdout
        assert "0 keeps Z3 without a finite timeout" in result.stdout
        assert "return before a non-trivial proof search" not in result.stdout

    def test_inspect_rejects_bmc_search_in_automatic_verify(
        self,
        inspect_code_file,
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            "json",
            "--enable-verify",
            "--max-complexity-tier",
            "bmc_search",
        )

        assert result.exitcode != 0
        assert "bmc_search algorithms are not allowed" in (
            result.stderr or result.stdout
        )

    def test_inspect_rejects_bmc_search_without_enable_verify(
        self,
        inspect_code_file,
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--max-complexity-tier",
            "bmc_search",
        )

        assert result.exitcode != 0
        assert "bmc_search algorithms are not allowed" in (
            result.stderr or result.stdout
        )

    def test_inspect_rejects_forbidden_policy_before_reading_input(self):
        result = _run_inspect(
            "-i",
            "/missing/inspect_case.fcstm",
            "--max-complexity-tier",
            "bmc_search",
        )

        assert result.exitcode != 0
        assert "bmc_search algorithms are not allowed" in (
            result.stderr or result.stdout
        )
        assert "Input DSL file not found" not in (result.stderr or result.stdout)

    def test_build_inspect_json_rejects_unknown_policy_before_reading_input(self):
        with pytest.raises(
            ClickErrorException, match="unknown inspect complexity tier"
        ):
            build_inspect_json(
                "/missing/inspect_case.fcstm",
                max_complexity_tier="unknown_tier",
            )

    def test_build_inspect_json_rejects_unknown_call_count_before_reading_input(self):
        with pytest.raises(
            ClickErrorException, match="unknown inspect call-count scaling"
        ):
            build_inspect_json(
                "/missing/inspect_case.fcstm",
                max_call_count_scaling="unknown_scaling",
            )

    @pytest.mark.parametrize(
        "call_count_scaling",
        [
            "k_unrollings",
            "k_unrollings_times_branching",
        ],
    )
    def test_inspect_rejects_invalid_call_count_scaling(
        self,
        inspect_code_file,
        call_count_scaling,
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--enable-verify",
            "--max-call-count-scaling",
            call_count_scaling,
        )

        assert result.exitcode != 0
        assert call_count_scaling in (result.stderr or result.stdout)

    def test_inspect_rejects_invalid_call_count_scaling_without_enable_verify(
        self,
        inspect_code_file,
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--max-call-count-scaling",
            "k_unrollings",
        )

        assert result.exitcode != 0
        assert "k_unrollings" in (result.stderr or result.stdout)

    def test_inspect_accepts_zero_smt_timeout(self, inspect_code_file):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            "json",
            "--enable-verify",
            "--max-complexity-tier",
            "smt_linear",
            "--smt-timeout-ms",
            "0",
        )

        assert result.exitcode == 0
        payload = _json_from_stdout(result)
        assert payload["root_state_path"] == "Root"

    def test_inspect_writes_json_to_output_file(self, inspect_code_file):
        with isolated_directory():
            result = _run_inspect(
                "-i",
                inspect_code_file,
                "--format",
                "json",
                "-o",
                "inspect_report.json",
            )

            assert result.exitcode == 0
            assert result.stdout == ""
            assert result.stderr == ""
            with open("inspect_report.json", "r", encoding="utf-8") as f:
                payload = json.load(f)
            assert payload["root_state_path"] == "Root"

    def test_inspect_output_file_overwrites_existing_file(self, inspect_code_file):
        with isolated_directory():
            with open("inspect_report.json", "w", encoding="utf-8") as f:
                f.write("old content")

            result = _run_inspect(
                "-i",
                inspect_code_file,
                "--format",
                "json",
                "-o",
                "inspect_report.json",
            )

            assert result.exitcode == 0
            with open("inspect_report.json", "r", encoding="utf-8") as f:
                payload = json.load(f)
            assert payload["root_state_path"] == "Root"

    def test_inspect_default_human_to_json_file_warns(self, inspect_code_file):
        with isolated_directory():
            result = _run_inspect(
                "-i",
                inspect_code_file,
                "-o",
                "inspect_report.json",
            )

            assert result.exitcode == 0
            assert result.stdout == ""
            assert "Warning:" in result.stderr
            assert "--format json" in result.stderr
            with open("inspect_report.json", "r", encoding="utf-8") as f:
                text = f.read()
            assert "FCSTM Inspect Report" in text
            with pytest.raises(json.JSONDecodeError):
                json.loads(text)

    def test_inspect_json_to_markdown_file_warns_without_stdout_pollution(
        self, inspect_code_file
    ):
        with isolated_directory():
            result = _run_inspect(
                "-i",
                inspect_code_file,
                "--format",
                "json",
                "-o",
                "inspect_report.md",
            )

            assert result.exitcode == 0
            assert result.stdout == ""
            assert "Warning:" in result.stderr
            with open("inspect_report.md", "r", encoding="utf-8") as f:
                payload = json.load(f)
            assert payload["root_state_path"] == "Root"

    def test_inspect_missing_input_file_is_controlled_error(self):
        result = _run_inspect("-i", "/missing/inspect_case.fcstm")

        assert result.exitcode != 0
        assert "Input DSL file not found" in (result.stderr or result.stdout)

    def test_inspect_parse_failure_is_controlled_error(self):
        with TemporaryDirectory() as td:
            code_file = os.path.join(td, "broken.fcstm")
            with open(code_file, "w", encoding="utf-8") as f:
                f.write("state Root {")

            result = _run_inspect("-i", code_file)

        assert result.exitcode != 0
        assert "Failed to parse input DSL file" in (result.stderr or result.stdout)

    def test_inspect_model_validation_failure_is_controlled_error(self):
        with TemporaryDirectory() as td:
            code_file = os.path.join(td, "invalid_model.fcstm")
            with open(code_file, "w", encoding="utf-8") as f:
                f.write("state Root { state Idle; state Idle; }")

            result = _run_inspect("-i", code_file)

        assert result.exitcode != 0
        assert "Invalid state machine model" in (result.stderr or result.stdout)

    def test_inspect_import_decode_error_reports_imported_file(self):
        with TemporaryDirectory() as td:
            code_file = os.path.join(td, "host.fcstm")
            imported_file = os.path.join(td, "bad.fcstm")
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(
                    textwrap.dedent("""
                        state Host {
                            import "./bad.fcstm" as Bad;
                            [*] -> Bad;
                        }
                    """).strip()
                )
            with open(imported_file, "wb") as f:
                f.write(b"\x81")

            result = _run_inspect("-i", code_file)

        output = result.stderr or result.stdout
        assert result.exitcode != 0
        assert "Invalid state machine model" in output
        assert "Failed to decode imported file" in output
        assert "bad.fcstm" in output
        assert "Failed to decode input DSL file" not in output

    def test_build_inspect_json_read_error_is_controlled_error(self, monkeypatch):
        def _raise_os_error(_input_code_file):
            raise OSError("permission denied")

        monkeypatch.setattr(
            "pyfcstm.entry.inspect.load_state_machine_from_file",
            _raise_os_error,
        )

        with pytest.raises(ClickErrorException, match="Failed to read input DSL file"):
            build_inspect_json("unreadable.fcstm")

    def test_build_inspect_json_decode_error_is_controlled_error(self, monkeypatch):
        def _raise_decode_error(_input_code_file):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        monkeypatch.setattr(
            "pyfcstm.entry.inspect.load_state_machine_from_file",
            _raise_decode_error,
        )

        with pytest.raises(
            ClickErrorException, match="Failed to decode input DSL file"
        ):
            build_inspect_json("invalid_encoding.fcstm")

    def test_inspect_output_write_failure_is_controlled_error(self, inspect_code_file):
        with isolated_directory():
            result = _run_inspect(
                "-i",
                inspect_code_file,
                "-o",
                "missing/report.json",
            )

        assert result.exitcode != 0
        assert "Failed to write inspect output file" in (result.stderr or result.stdout)
