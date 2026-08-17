import json
import os
import re
import subprocess
import sys
import textwrap
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest
from hbutils.testing import isolated_directory, simulate_entry

from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.base import ClickErrorException
from pyfcstm.diagnostics.inspect_render import INSPECT_LLM_SCHEMA_VERSION
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
        assert "[WARN] FCSTM Inspect Report" in result.stdout
        assert "status: warning" in result.stdout
        assert "W_LEAF_NO_OUTGOING_TRANSITION" in result.stdout
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
        assert "[WARN]" in ANSI_ESCAPE_RE.sub("", result.stdout)

    def test_inspect_human_color_never_outputs_plain_text(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--color", "never")

        assert result.exitcode == 0
        assert not _has_ansi(result.stdout)
        assert "[WARN] FCSTM Inspect Report" in result.stdout

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
            assert "[WARN] FCSTM Inspect Report" in text

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
        assert payload["verification"] == {
            "supported": True,
            "enabled": False,
            "provider": "pyfcstm.verify",
            "reason_code": "verification_disabled",
            "requested_policy": {
                "max_complexity_tier": "structural",
                "max_call_count_scaling": "linear_in_transitions",
                "smt_timeout_ms": None,
            },
            "summary": {
                "registered": None,
                "executed": 0,
                "not_run": 0,
                "indeterminate": 0,
            },
            "algorithms": [],
        }

    def test_inspect_enable_verify_reports_structural_coverage(self, inspect_code_file):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            "json",
            "--enable-verify",
        )

        assert result.exitcode == 0
        summary = _json_from_stdout(result)["verification"]["summary"]
        assert summary == {
            "registered": 14,
            "executed": 6,
            "not_run": 8,
            "indeterminate": 0,
        }

    def test_inspect_enable_smt_linear_reports_complete_coverage(self, inspect_code_file):
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
        verification = _json_from_stdout(result)["verification"]
        assert verification["summary"] == {
            "registered": 14,
            "executed": 14,
            "not_run": 0,
            "indeterminate": 0,
        }

    def test_indeterminate_verification_does_not_change_cli_exit_code(
        self, monkeypatch, inspect_code_file
    ):
        import pyfcstm.entry.inspect as inspect_entry_module

        monkeypatch.setattr(
            inspect_entry_module,
            "_build_inspect_output_with_report",
            lambda *args, **kwargs: (
                "verification: 1/1 run, 0 not run by policy, 1 indeterminate\n",
                SimpleNamespace(diagnostics=()),
            ),
        )

        result = _run_inspect(
            "-i", inspect_code_file, "--enable-verify", "--format", "human"
        )

        assert result.exitcode == 0

    def test_inspect_format_llm_json_outputs_stable_packet(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--format", "llm-json")

        assert result.exitcode == 0
        assert not _has_ansi(result.stdout)
        payload = _json_from_stdout(result)
        assert payload["schema_version"] == INSPECT_LLM_SCHEMA_VERSION
        assert payload["schema_status"] == "stable"
        assert payload["status"] == "warning"
        assert payload["diagnostics"]
        diagnostic = payload["diagnostics"][0]
        assert "source_excerpt" in diagnostic
        assert "context" in diagnostic["source_excerpt"]
        assert any(
            line["is_anchor"] and line["caret"]
            for line in diagnostic["source_excerpt"]["context"]
        )
        assert "for_llm" not in payload

    def test_inspect_format_llm_md_outputs_stable_markdown(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--format", "llm-md")

        assert result.exitcode == 0
        assert not _has_ansi(result.stdout)
        assert "# FCSTM Inspect Report" in result.stdout
        assert INSPECT_LLM_SCHEMA_VERSION in result.stdout
        assert "Recommended actions" in result.stdout
        assert "Repair notes" in result.stdout
        assert "Schema status: `stable`" in result.stdout
        assert "|     ^" in result.stdout

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
        assert verify_diagnostics[0]["provenance"] == {
            "kind": "verify-backed",
            "verify_required": True,
        }
        assert verify_diagnostics[0]["repair_guidance"]

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
        assert "[WARN] W_DEAD_GUARD" in result.stdout
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

    @pytest.mark.parametrize(
        ("option", "obsolete_choice"),
        [
            ("--max-complexity-tier", "bmc_search"),
            ("--max-call-count-scaling", "k_unrollings"),
            ("--max-call-count-scaling", "k_unrollings_times_branching"),
        ],
    )
    def test_inspect_rejects_obsolete_policy_as_click_usage_error(
        self, option, obsolete_choice
    ):
        result = _run_inspect(
            "-i",
            "/missing/inspect_case.fcstm",
            option,
            obsolete_choice,
        )

        output = result.stderr or result.stdout
        assert result.exitcode == 2
        assert "Invalid value for" in output
        assert obsolete_choice in output
        assert "Input DSL file not found" not in output
        assert "not allowed in automatic inspect runs" not in output

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

    def test_inspect_rejects_negative_smt_timeout(self, inspect_code_file):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--format",
            "json",
            "--smt-timeout-ms",
            "-1",
        )

        assert result.exitcode != 0
        assert "-1 is not in the range x>=0" in (result.stdout + result.stderr)

    def test_successful_highest_budget_cli_does_not_load_bmc(self, inspect_code_file):
        script = """
import json
import sys

from hbutils.testing import simulate_entry
from pyfcstm.entry import pyfcstmcli

result = simulate_entry(pyfcstmcli, [
    'pyfcstm', 'inspect', '-i', sys.argv[1], '--format', 'json',
    '--enable-verify', '--max-complexity-tier', 'smt_undecidable_heuristic',
    '--max-call-count-scaling', 'vars_times_transitions',
    '--smt-timeout-ms', '1000',
])
if result.exitcode != 0:
    raise SystemExit(result.stdout + result.stderr)
json.loads(result.stdout)
loaded = sorted(
    name for name in sys.modules
    if name == 'pyfcstm.bmc' or name.startswith('pyfcstm.bmc.')
)
if loaded:
    raise SystemExit('\\n'.join(loaded))
"""
        result = subprocess.run(
            [sys.executable, "-c", script, inspect_code_file],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr

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


_MULTI_ERROR_DSL = textwrap.dedent("""
    state Root {
        state A;
        state A;
        NoSuch -> A;
        state Outer { state Inner; }
        [*] -> A;
    }
""").strip()


@pytest.fixture()
def multi_error_code_file():
    """A model carrying three distinct ``E_*`` codes in one file."""
    with TemporaryDirectory() as td:
        code_file = os.path.join(td, "multi_error.fcstm")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(_MULTI_ERROR_DSL)
        yield code_file


@pytest.mark.unittest
class TestInspectCollectErrors:
    """``--collect-errors`` reports every ``E_*`` instead of only the first.

    Strict model building raises on the first error, so an inspect report can
    never carry more than one. The collecting path accumulates all of them and
    still finishes with a non-zero exit code.
    """

    def test_json_reports_every_error_code(self, multi_error_code_file):
        payload = json.loads(
            build_inspect_json(multi_error_code_file, collect_errors=True)
        )

        codes = {item["code"] for item in payload["diagnostics"]}
        assert {
            "E_DUPLICATE_STATE",
            "E_DANGLING_TRANSITION",
            "E_INITIAL_TRANSITION_INVALID",
        } <= codes

    def test_cli_reports_every_error_code(self, multi_error_code_file):
        result = _run_inspect("-i", multi_error_code_file, "--collect-errors")

        assert "E_DUPLICATE_STATE" in result.stdout
        assert "E_DANGLING_TRANSITION" in result.stdout
        assert "E_INITIAL_TRANSITION_INVALID" in result.stdout

    def test_cli_still_exits_non_zero(self, multi_error_code_file):
        result = _run_inspect("-i", multi_error_code_file, "--collect-errors")

        assert result.exitcode != 0
        # Not a usage error: the report itself was produced and the non-zero
        # code comes from the error-severity diagnostics inside it.
        assert "no such option" not in (result.stderr or "").lower()
        assert "FCSTM Inspect Report" in result.stdout

    def test_cli_exits_zero_on_a_clean_model(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file, "--collect-errors")

        assert result.exitcode == 0

    def test_cli_json_carries_the_errors(self, multi_error_code_file):
        result = _run_inspect(
            "-i", multi_error_code_file, "--collect-errors", "--format", "json"
        )

        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["diagnostics"]}
        assert {
            "E_DUPLICATE_STATE",
            "E_DANGLING_TRANSITION",
            "E_INITIAL_TRANSITION_INVALID",
        } <= codes

    def test_default_run_stays_a_controlled_single_error(self, multi_error_code_file):
        result = _run_inspect("-i", multi_error_code_file)

        assert result.exitcode != 0
        assert "Invalid state machine model" in (result.stderr or result.stdout)
        assert "E_DANGLING_TRANSITION" not in (result.stderr or result.stdout)

    @pytest.mark.parametrize('output_format', ['human', 'json', 'llm-json', 'llm-md'])
    def test_every_format_carries_the_errors(
        self, multi_error_code_file, output_format
    ):
        result = _run_inspect(
            '-i', multi_error_code_file, '--collect-errors',
            '--format', output_format,
        )

        assert result.exitcode != 0
        assert 'E_DUPLICATE_STATE' in result.stdout
        assert 'E_DANGLING_TRANSITION' in result.stdout

    @pytest.mark.parametrize('output_format', ['human', 'json', 'llm-json', 'llm-md'])
    def test_output_file_is_written_before_the_exit_code_is_set(
        self, multi_error_code_file, output_format
    ):
        """The report must survive the non-zero exit, not be skipped by it."""
        with TemporaryDirectory() as td:
            out_path = os.path.join(td, f'report.{output_format}')

            result = _run_inspect(
                '-i', multi_error_code_file, '--collect-errors',
                '--format', output_format, '-o', out_path,
            )

            assert result.exitcode != 0
            assert os.path.exists(out_path)
            with open(out_path, encoding='utf-8') as f:
                body = f.read()

        assert 'E_DUPLICATE_STATE' in body
        assert 'E_DANGLING_TRANSITION' in body

    def test_a_syntax_error_still_fails_before_any_report(self):
        """Collection covers model errors, not parse errors.

        A file that does not parse has no AST to build a model from, so there is
        nothing to collect and the run must still stop at the parse failure.
        """
        with TemporaryDirectory() as td:
            code_file = os.path.join(td, 'broken.fcstm')
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write('state Root {')

            result = _run_inspect('-i', code_file, '--collect-errors')

        assert result.exitcode != 0
        assert 'Failed to parse input DSL file' in (result.stderr or result.stdout)

    def test_error_severity_rendering_is_exercised_for_the_first_time(
        self, multi_error_code_file
    ):
        """Collecting errors activates render paths that were unreachable.

        The renderer has always had an ``error`` entry in its severity order,
        human label, status map and ANSI style table, but an inspect report could
        never carry an error-severity diagnostic, so none of it ran. These
        assertions cover that newly reachable path.
        """
        text = build_inspect_output(
            multi_error_code_file,
            output_format="human",
            collect_errors=True,
            color_enabled=False,
        )
        colored = build_inspect_output(
            multi_error_code_file,
            output_format="human",
            collect_errors=True,
            color_enabled=True,
        )

        assert "[ERROR] FCSTM Inspect Report" in text
        assert "status: error" in text
        assert not _has_ansi(text)
        assert _has_ansi(colored)

    def test_llm_json_counts_the_errors(self, multi_error_code_file):
        payload = json.loads(
            build_inspect_output(
                multi_error_code_file,
                output_format="llm-json",
                collect_errors=True,
            )
        )

        assert payload["status"] == "error"
        assert payload["summary"]["errors"] >= 2
