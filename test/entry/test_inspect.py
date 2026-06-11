import json
import os
import textwrap
from tempfile import TemporaryDirectory

import pytest
from hbutils.testing import isolated_directory, simulate_entry

from pyfcstm.entry import pyfcstmcli


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


@pytest.mark.unittest
class TestEntryInspect:
    def test_inspect_outputs_default_json_to_stdout(self, inspect_code_file):
        result = _run_inspect("-i", inspect_code_file)

        assert result.exitcode == 0
        payload = _json_from_stdout(result)
        assert payload["root_state_path"] == "Root"
        assert payload["states"]
        assert payload["transitions"]
        assert "reachability_graph" in payload
        assert "diagnostics" in payload
        assert "W_DEAD_GUARD" not in {
            diagnostic["code"] for diagnostic in payload["diagnostics"]
        }

    def test_inspect_enable_verify_exposes_verify_diagnostics(self, inspect_code_file):
        result = _run_inspect(
            "-i",
            inspect_code_file,
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

    def test_inspect_rejects_bmc_search_in_automatic_verify(
        self,
        inspect_code_file,
    ):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--enable-verify",
            "--max-complexity-tier",
            "bmc_search",
        )

        assert result.exitcode != 0
        assert "bmc_search algorithms are not allowed" in (
            result.stderr or result.stdout
        )

    def test_inspect_rejects_invalid_call_count_scaling(self, inspect_code_file):
        result = _run_inspect(
            "-i",
            inspect_code_file,
            "--enable-verify",
            "--max-call-count-scaling",
            "k_unrollings",
        )

        assert result.exitcode != 0
        assert "k_unrollings" in (result.stderr or result.stdout)

    def test_inspect_writes_json_to_output_file(self, inspect_code_file):
        with isolated_directory():
            result = _run_inspect(
                "-i",
                inspect_code_file,
                "-o",
                "inspect_report.json",
            )

            assert result.exitcode == 0
            assert result.stdout == ""
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
                "-o",
                "inspect_report.json",
            )

            assert result.exitcode == 0
            with open("inspect_report.json", "r", encoding="utf-8") as f:
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

    def test_inspect_output_write_failure_is_controlled_error(self, inspect_code_file):
        with isolated_directory():
            result = _run_inspect(
                "-i",
                inspect_code_file,
                "-o",
                "missing/report.json",
            )

        assert result.exitcode != 0
        assert "Failed to write inspect JSON file" in (
            result.stderr or result.stdout
        )
