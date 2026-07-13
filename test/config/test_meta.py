import pytest

import pyfcstm
from pyfcstm.config.meta import __TITLE__, __VERSION__


@pytest.mark.unittest
class TestConfigMeta:
    def test_title(self):
        assert __TITLE__ == "pyfcstm"

    def test_package_version_export_matches_release_version(self):
        assert __VERSION__ == "0.6.0"
        assert pyfcstm.__version__ == __VERSION__
