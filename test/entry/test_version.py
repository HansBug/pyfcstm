import textwrap

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.config.meta import __VERSION__
from pyfcstm.entry.dispatch import pyfcstmcli


@pytest.mark.unittest
class TestEntryVersion:
    def test_cli_version(self, text_aligner):
        result = simulate_entry(pyfcstmcli, [
            'pyfcstm', '-v',
        ])
        assert result.exitcode == 0
        text_aligner.assert_equal(
            expect=textwrap.dedent(f"""
                Pyfcstm, version {__VERSION__}.
                Developed by HansBug (hansbug@buaa.edu.cn).
            """).strip(),
            actual=result.stdout
        )
