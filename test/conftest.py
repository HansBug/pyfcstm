import os

import pytest
from hbutils.testing import TextAligner


_SLOW_TEST_PATH_PREFIXES = (
    os.path.join("test", "template", "c", ""),
    os.path.join("test", "template", "c_poll", ""),
    os.path.join("test", "template", "cpp", ""),
    os.path.join("test", "template", "cpp_poll", ""),
)


def _is_slow_path(nodeid: str) -> bool:
    norm = nodeid.replace("\\", "/").replace("/", os.sep)
    for prefix in _SLOW_TEST_PATH_PREFIXES:
        if norm.startswith(prefix) or norm.startswith(prefix.replace(os.sep, "/")):
            return True
    if any(
        prefix.replace(os.sep, "/") in nodeid.replace("\\", "/")
        for prefix in _SLOW_TEST_PATH_PREFIXES
    ):
        return True
    return False


def pytest_addoption(parser):
    """Register repository-wide pytest switches.

    :param parser: pytest option parser.
    :type parser: pytest.Parser
    :return: ``None``.
    :rtype: None
    """
    parser.addoption(
        "--run-native-toolchain",
        action="store_true",
        default=False,
        help="Run explicit native toolchain alignment tests.",
    )


def pytest_generate_tests(metafunc):
    """Parametrize explicit native toolchain semantic cases lazily.

    :param metafunc: pytest metafunc object.
    :type metafunc: pytest.Metafunc
    :return: ``None``.
    :rtype: None
    """
    if "native_semantic_case_id" not in metafunc.fixturenames:
        return
    from test.testings.native_toolchain_alignment.profiles import (
        native_toolchain_enabled,
        resolve_selected_profile,
    )

    if not native_toolchain_enabled(metafunc.config):
        metafunc.parametrize(
            "native_semantic_case_id",
            [
                pytest.param(
                    None,
                    marks=pytest.mark.skip(
                        reason="native toolchain matrix requires explicit opt-in"
                    ),
                )
            ],
            ids=["native-toolchain-disabled"],
        )
        return

    # Fail early when native toolchain tests are explicitly enabled without a
    # valid profile. This avoids a false-green collection that silently runs no
    # native profile.
    resolve_selected_profile(metafunc.config)
    from test.testings.simulate_semantics import iter_semantic_cases

    case_ids = [case.id for case in iter_semantic_cases()]
    metafunc.parametrize("native_semantic_case_id", case_ids, ids=case_ids)


def pytest_collection_modifyitems(config, items):
    """Auto-mark native C-family template tests and apply skip gates.

    ``SKIP_SLOW_TESTS=1`` skips ordinary native C-family template tests by
    path, but explicitly enabled ``native_toolchain`` items take priority so
    explicit native toolchain workflow runs are not accidentally converted into
    false-green skips.
    """
    from test.testings.native_toolchain_alignment.profiles import (
        native_toolchain_enabled,
    )

    native_enabled = native_toolchain_enabled(config)
    slow_marker = pytest.mark.slow
    skip_slow = os.environ.get("SKIP_SLOW_TESTS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    skip_marker = pytest.mark.skip(
        reason="SKIP_SLOW_TESTS=1 — native C-family template tests skipped"
    )
    native_disabled_marker = pytest.mark.skip(
        reason="native toolchain matrix requires explicit opt-in"
    )

    for item in items:
        is_native_toolchain = "native_toolchain" in item.keywords
        if is_native_toolchain and not native_enabled:
            item.add_marker(native_disabled_marker)
        if _is_slow_path(item.nodeid):
            item.add_marker(slow_marker)
            if skip_slow and not is_native_toolchain:
                item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def text_aligner():
    return TextAligner()
