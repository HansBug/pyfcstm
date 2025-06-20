import pytest
from hbutils.testing import isolated_directory

from pyfcstm.utils import is_binary_file
from test.testings import get_testfile


@pytest.mark.unittest
class TestUtilsBinary:
    def test_is_binary_file(self):
        assert is_binary_file(get_testfile('shu.jpg'))
        assert not is_binary_file('README.md')

        with isolated_directory():
            with open('file', 'w'):
                pass

            assert not is_binary_file('file')
