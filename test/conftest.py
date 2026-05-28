import os

import pytest
from hbutils.testing import TextAligner


_SLOW_TEST_PATH_PREFIXES = (
    os.path.join('test', 'template', 'c', ''),
    os.path.join('test', 'template', 'c_poll', ''),
)


def _is_slow_path(nodeid: str) -> bool:
    norm = nodeid.replace('\\', '/').replace('/', os.sep)
    for prefix in _SLOW_TEST_PATH_PREFIXES:
        if norm.startswith(prefix) or norm.startswith(prefix.replace(os.sep, '/')):
            return True
    if any(prefix.replace(os.sep, '/') in nodeid.replace('\\', '/') for prefix in _SLOW_TEST_PATH_PREFIXES):
        return True
    return False


def pytest_collection_modifyitems(config, items):
    """Auto-mark native-toolchain template tests as ``slow`` and optionally skip them.

    When ``SKIP_SLOW_TESTS=1`` is set (e.g. CI commit message contains
    ``[skip-slow]``), tests under ``test/template/c`` and ``test/template/c_poll``
    are skipped because they invoke real ``cmake`` / ``cc`` compilation per case.
    """
    slow_marker = pytest.mark.slow
    skip_slow = os.environ.get('SKIP_SLOW_TESTS', '').strip().lower() in ('1', 'true', 'yes', 'on')
    skip_marker = pytest.mark.skip(reason='SKIP_SLOW_TESTS=1 — native-toolchain template tests skipped')

    for item in items:
        if _is_slow_path(item.nodeid):
            item.add_marker(slow_marker)
            if skip_slow:
                item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def text_aligner():
    return TextAligner()
