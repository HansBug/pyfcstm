import pytest
from hbutils.testing import TextAligner


@pytest.fixture(scope='session')
def text_aligner():
    return TextAligner()
