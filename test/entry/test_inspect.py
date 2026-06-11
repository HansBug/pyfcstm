import json
import os
import textwrap
from tempfile import TemporaryDirectory

import pytest
from hbutils.testing import isolated_directory, simulate_entry

from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.base import ClickErrorException
from pyfcstm.entry.inspect import build_inspect_json


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
        with pytest.raises(ClickErrorException, match="unknown inspect complexity tier"):
            build_inspect_json(
                "/missing/inspect_case.fcstm",
                max_complexity_tier="unknown_tier",
            )

    def test_build_inspect_json_rejects_unknown_call_count_before_reading_input(self):
        with pytest.raises(ClickErrorException, match="unknown_scaling"):
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

    def test_inspect_model_validation_failure_is_controlled_error(self):
        with TemporaryDirectory() as td:
            code_file = os.path.join(td, "invalid_model.fcstm")
            with open(code_file, "w", encoding="utf-8") as f:
                f.write("state Root { state Idle; state Idle; }")

            result = _run_inspect("-i", code_file)

        assert result.exitcode != 0
        assert "Invalid state machine model" in (result.stderr or result.stdout)

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

        with pytest.raises(ClickErrorException, match="Failed to decode input DSL file"):
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
        assert "Failed to write inspect JSON file" in (
            result.stderr or result.stdout
        )
