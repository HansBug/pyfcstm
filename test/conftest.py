import os

import pytest
from hbutils.testing import TextAligner


_SKIP_SLOW_TEST_PATH_PREFIXES = (
    os.path.join("test", "template", "c", ""),
    os.path.join("test", "template", "c_poll", ""),
    os.path.join("test", "template", "cpp", "test_semantic_fixture_alignment.py"),
    os.path.join(
        "test", "template", "cpp_poll", "test_semantic_fixture_alignment.py"
    ),
    os.path.join("test", "template", "cpp", "test_native_toolchain_alignment.py"),
    os.path.join(
        "test", "template", "cpp_poll", "test_native_toolchain_alignment.py"
    ),
)
_SLOW_TEST_PATH_PREFIXES = _SKIP_SLOW_TEST_PATH_PREFIXES


def _matches_path_prefix(nodeid: str, prefixes) -> bool:
    """Return whether a pytest node id belongs to one path prefix.

    :param nodeid: Pytest item node id.
    :type nodeid: str
    :param prefixes: Path prefixes using the platform separator.
    :type prefixes: collections.abc.Sequence[str]
    :return: ``True`` when ``nodeid`` starts with or contains a prefix.
    :rtype: bool
    """
    norm = nodeid.replace("\\", "/").replace("/", os.sep)
    for prefix in prefixes:
        if norm.startswith(prefix) or norm.startswith(prefix.replace(os.sep, "/")):
            return True
    if any(
        prefix.replace(os.sep, "/") in nodeid.replace("\\", "/")
        for prefix in prefixes
    ):
        return True
    return False


def _is_slow_path(nodeid: str) -> bool:
    """Return whether a pytest node id should be marked slow.

    :param nodeid: Pytest item node id.
    :type nodeid: str
    :return: ``True`` when the item belongs to a slow template path.
    :rtype: bool
    """
    return _matches_path_prefix(nodeid, _SLOW_TEST_PATH_PREFIXES)


def _is_skip_slow_path(nodeid: str) -> bool:
    """Return whether ``SKIP_SLOW_TESTS`` should skip a pytest node id.

    :param nodeid: Pytest item node id.
    :type nodeid: str
    :return: ``True`` when the item belongs to the fast-path skip set.
    :rtype: bool
    """
    return _matches_path_prefix(nodeid, _SKIP_SLOW_TEST_PATH_PREFIXES)


#: Marker that puts a test into the suite ``make unittest`` runs via ``-m unittest``.
_SUITE_MARKER = "unittest"

#: Markers that declare a test to be deliberately outside that suite. ``native_toolchain``
#: tests need an explicit opt-in, and ``benchmark`` / ``ignore`` are reserved in
#: ``pytest.ini`` for the same purpose. Carrying one of these is a statement of intent, so
#: it satisfies the gate below in place of :data:`_SUITE_MARKER`.
_OUT_OF_SUITE_MARKERS = frozenset({"native_toolchain", "benchmark", "ignore"})


def _items_no_selector_reaches(items):
    """Return node ids that neither ``-m unittest`` nor an opt-in selector would run.

    A test carrying none of the known selection markers is collected by a bare
    ``pytest`` run and silently dropped by ``make unittest``, so deleting the code it
    covers leaves the suite green. Reporting the node ids rather than a count is what
    lets the failure name the modules that have to be fixed.

    Markers are read through ``iter_markers`` rather than ``keywords``, because
    ``keywords`` also holds names and parametrisation ids: a test whose param id happened
    to be ``unittest`` would satisfy a keyword check while carrying no marker at all, and
    the gate would wave through exactly the module it exists to catch. ``iter_markers``
    reports real markers only, and still sees a module-level ``pytestmark`` because it
    walks the node chain.

    :param items: Collected pytest items.
    :type items: collections.abc.Iterable[pytest.Item]
    :return: Node ids of items no selector reaches, in collection order.
    :rtype: list[str]
    """
    unreached = []
    for item in items:
        names = {marker.name for marker in item.iter_markers()}
        if _SUITE_MARKER in names:
            continue
        if names & _OUT_OF_SUITE_MARKERS:
            continue
        unreached.append(item.nodeid)
    return unreached


def _unreached_items_message(nodeids) -> str:
    """Build the collection-failure text for items no selector reaches.

    :param nodeids: Node ids no selector reaches.
    :type nodeids: collections.abc.Sequence[str]
    :return: A message naming each offending module and its test count.
    :rtype: str
    """
    per_module = {}
    for nodeid in nodeids:
        per_module.setdefault(nodeid.split("::", 1)[0], []).append(nodeid)
    lines = [
        "%d test(s) carry no selection marker, so `make unittest` would silently "
        "skip them:" % len(nodeids)
    ]
    for module in sorted(per_module):
        lines.append("  %s (%d test(s))" % (module, len(per_module[module])))
    lines.append(
        "Add a module-level `pytestmark = pytest.mark.%s`, or one of %s when the "
        "test is deliberately outside that suite."
        % (_SUITE_MARKER, ", ".join(sorted(_OUT_OF_SUITE_MARKERS)))
    )
    return "\n".join(lines)


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
    """Reject unselectable tests, then auto-mark native C-family tests and apply skip gates.

    The selection-marker check runs first and aborts collection, because a test no
    selector reaches is invisible to ``make unittest`` rather than merely slow: the
    suite stays green after the code it covers is deleted. This hook sees every
    collected item before ``-m`` deselection removes any, which is what lets it name
    the modules instead of reporting a count that has already been filtered.

    ``SKIP_SLOW_TESTS=1`` skips ordinary C-family native-template tests by
    path, but explicitly enabled ``native_toolchain`` items take priority so
    explicit native toolchain workflow runs are not accidentally converted into
    false-green skips. C++ wrapper smoke tests remain outside the broad skip
    path, so fast template iterations still exercise the wrapper APIs without
    the all-fixture native build cost.
    """
    from test.testings.native_toolchain_alignment.profiles import (
        native_toolchain_enabled,
    )

    unreached = _items_no_selector_reaches(items)
    if unreached:
        raise pytest.UsageError(_unreached_items_message(unreached))

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
        if skip_slow and _is_skip_slow_path(item.nodeid) and not is_native_toolchain:
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def text_aligner():
    return TextAligner()
