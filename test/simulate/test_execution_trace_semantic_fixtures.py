"""The optional trace preserves every existing simulator fixture's behavior."""

from dataclasses import replace

import pytest

from test.testings import simulate_semantics as fixtures


pytestmark = pytest.mark.unittest


@pytest.mark.parametrize(
    "case",
    [
        case
        for case in fixtures.iter_semantic_cases(runners=["simulation"])
        # Constructor failures never reach cycle(), the trace entry point.
        if fixtures._initial_constructor_expect(case) is None
    ],
    ids=lambda case: case.id,
)
@pytest.mark.parametrize("diagnostics", [False, True])
def test_trace_preserves_semantic_fixture(case, monkeypatch, diagnostics):
    plain = fixtures._build_simulation_runtime(case)
    traced = fixtures._build_simulation_runtime(case)
    plain_calls = fixtures._register_fixture_handlers(plain, case)
    traced_calls = fixtures._register_fixture_handlers(traced, case)
    plain_cycle = plain.cycle
    traced_cycle = traced.cycle
    plain_results = []
    traced_results = []
    snapshots = []
    decision_snapshots = []

    def without_trace(events=None, **kwargs):
        result = plain_cycle(events, **kwargs)
        plain_results.append(result)
        return result

    def with_trace(events=None, **kwargs):
        result = traced_cycle(events, trace=True, diagnostics=diagnostics, **kwargs)
        traced_results.append(result)
        snapshots.append([entry.to_dict() for entry in result.trace])
        if diagnostics:
            decision_snapshots.append(result.diagnostics.to_dict())
        if result.delta:
            assert result.trace == ()
        return result

    # Only observe public calls and enable the public keyword argument. The
    # shared runner still owns event resolution and independent YAML assertions,
    # including expected errors; no production helper or state is replaced.
    monkeypatch.setattr(plain, "cycle", without_trace)
    monkeypatch.setattr(traced, "cycle", with_trace)
    for index, step in enumerate(case.data.get("steps") or []):
        fixtures._run_step(plain, step, case, index, handler_calls=plain_calls)
        fixtures._run_step(traced, step, case, index, handler_calls=traced_calls)
        assert traced.vars == plain.vars
        assert traced.brief_stack == plain.brief_stack
        assert traced.history == plain.history
        assert traced.cycle_count == plain.cycle_count
        assert traced.is_ended == plain.is_ended
        assert traced_calls == plain_calls
        assert [replace(result, trace=(), diagnostics=None) for result in traced_results] == plain_results

    # Retain all results across the complete scenario to catch snapshots backed
    # by live mutable state, including a later failure or Delta boundary.
    assert [
        [entry.to_dict() for entry in result.trace] for result in traced_results
    ] == snapshots

    if diagnostics:
        assert [r.diagnostics.to_dict() for r in traced_results] == decision_snapshots
