import pytest
from hbutils.testing import simulate_entry

from pyfcstm._bootstrap import format_version_info
from pyfcstm.entry.dispatch import pyfcstmcli


@pytest.mark.unittest
class TestEntryVersion:
    def test_cli_version(self, text_aligner):
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "-v",
            ],
        )
        assert result.exitcode == 0
        text_aligner.assert_equal(expect=format_version_info(), actual=result.stdout)
