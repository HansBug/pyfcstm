"""CLI integration tests for ``pyfcstm topology``."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyfcstm.entry import pyfcstmcli


_LINEAR = """
state Root {
    state A;
    state B;
    state C;
    [*] -> A;
    A -> B;
    B -> C;
    C -> [*];
}
"""

_TRAP = """
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B;
    B -> A;
}
"""

_BRANCH = """
state Root {
    state Init;
    state Good;
    state Bad;
    [*] -> Init;
    Init -> Good;
    Init -> Bad;
    Good -> [*];
    Bad -> [*];
}
"""


@pytest.fixture
def write_dsl(tmp_path):
    def _write(content: str, name: str = "machine.fcstm") -> str:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return str(p)
    return _write


@pytest.fixture
def runner():
    return CliRunner()


@pytest.mark.unittest
class TestTopologyReachCli:
    def test_reach_happy_exit_zero(self, runner, write_dsl):
        path = write_dsl(_LINEAR)
        result = runner.invoke(pyfcstmcli, ['topology', 'reach', '-i', path, '-t', 'Root.C'])
        assert result.exit_code == 0
        assert '[reachable]' in result.output
        assert 'Root.A -> Root.B -> Root.C' in result.output

    def test_reach_fail_exit_one(self, runner, write_dsl):
        path = write_dsl(_LINEAR)
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'reach', '-i', path, '-t', 'Root.A', '-s', 'Root.C'],
        )
        assert result.exit_code == 1
        assert '[unreachable]' in result.output

    def test_reach_json_output(self, runner, write_dsl):
        path = write_dsl(_LINEAR)
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'reach', '-i', path, '-t', 'Root.B', '--format', 'json'],
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload['reachable'] is True
        assert payload['witness_path'] == ['Root.A', 'Root.B']

    def test_reach_unknown_target_exit_nonzero(self, runner, write_dsl):
        path = write_dsl(_LINEAR)
        result = runner.invoke(
            pyfcstmcli, ['topology', 'reach', '-i', path, '-t', 'Root.NotAState']
        )
        assert result.exit_code != 0


@pytest.mark.unittest
class TestTopologyFiniteCli:
    def test_finite_happy(self, runner, write_dsl):
        path = write_dsl(_LINEAR)
        result = runner.invoke(pyfcstmcli, ['topology', 'finite', '-i', path])
        assert result.exit_code == 0
        assert '[finite]' in result.output

    def test_finite_fail(self, runner, write_dsl):
        path = write_dsl(_TRAP)
        result = runner.invoke(pyfcstmcli, ['topology', 'finite', '-i', path])
        assert result.exit_code == 1
        assert '[infinite]' in result.output
        assert 'cycle' in result.output

    def test_finite_json(self, runner, write_dsl):
        path = write_dsl(_TRAP)
        result = runner.invoke(
            pyfcstmcli, ['topology', 'finite', '-i', path, '--format', 'json']
        )
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload['finite'] is False
        assert payload['counterexample']['kind'] == 'trap_cycle'


@pytest.mark.unittest
class TestTopologyInevitableCli:
    def test_inev_happy(self, runner, write_dsl):
        path = write_dsl(_LINEAR)
        result = runner.invoke(
            pyfcstmcli, ['topology', 'inevitable', '-i', path, '-t', 'Root.B']
        )
        assert result.exit_code == 0
        assert '[inevitable]' in result.output

    def test_inev_fail_alt_end(self, runner, write_dsl):
        path = write_dsl(_BRANCH)
        result = runner.invoke(
            pyfcstmcli, ['topology', 'inevitable', '-i', path, '-t', 'Root.Good']
        )
        assert result.exit_code == 1
        assert '[avoidable]' in result.output
        assert 'alt_end' in result.output

    def test_inev_json(self, runner, write_dsl):
        path = write_dsl(_BRANCH)
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'inevitable', '-i', path, '-t', 'Root.Good', '--format', 'json'],
        )
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload['counterexample']['kind'] == 'alt_end'
        assert payload['counterexample']['terminal'] == '[*]'

    def test_inev_with_source_flag(self, runner, write_dsl):
        path = write_dsl(_BRANCH)
        # From Bad, Bad IS inevitable.
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'inevitable', '-i', path, '-t', 'Root.Bad', '-s', 'Root.Bad'],
        )
        assert result.exit_code == 0


@pytest.mark.unittest
class TestTopologyGroupHelp:
    def test_topology_group_help(self, runner):
        result = runner.invoke(pyfcstmcli, ['topology', '-h'])
        assert result.exit_code == 0
        for sub in ('reach', 'finite', 'inevitable'):
            assert sub in result.output

    def test_missing_file_reports_error(self, runner):
        result = runner.invoke(
            pyfcstmcli, ['topology', 'reach', '-i', '/tmp/__no_such_file__.fcstm', '-t', 'Root.A']
        )
        assert result.exit_code != 0


@pytest.mark.unittest
class TestTopologyVisualization:
    def test_reach_writes_svg(self, runner, write_dsl, tmp_path):
        path = write_dsl(_LINEAR)
        out = tmp_path / "out.svg"
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'reach', '-i', path, '-t', 'Root.C', '-o', str(out)],
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert content.startswith('<?xml')
        assert '<svg' in content

    def test_reach_fail_still_writes_svg(self, runner, write_dsl, tmp_path):
        path = write_dsl(_LINEAR)
        out = tmp_path / "out.svg"
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'reach', '-i', path, '-t', 'Root.A', '-s', 'Root.C', '-o', str(out)],
        )
        # Property violated → exit 1 but file is still written.
        assert result.exit_code == 1
        assert out.exists()
        assert '<svg' in out.read_text()

    def test_finite_writes_png(self, runner, write_dsl, tmp_path):
        path = write_dsl(_TRAP)
        out = tmp_path / "out.png"
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'finite', '-i', path, '-o', str(out)],
        )
        assert result.exit_code == 1
        png = out.read_bytes()
        assert png[:8] == b'\x89PNG\r\n\x1a\n'

    def test_inev_writes_png(self, runner, write_dsl, tmp_path):
        path = write_dsl(_BRANCH)
        out = tmp_path / "out.png"
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'inevitable', '-i', path, '-t', 'Root.Good', '-o', str(out)],
        )
        assert result.exit_code == 1
        assert out.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'

    def test_unknown_extension_errors(self, runner, write_dsl, tmp_path):
        path = write_dsl(_LINEAR)
        out = tmp_path / "out.gif"
        result = runner.invoke(
            pyfcstmcli,
            ['topology', 'reach', '-i', path, '-t', 'Root.C', '-o', str(out)],
        )
        assert result.exit_code != 0
        assert not out.exists()
