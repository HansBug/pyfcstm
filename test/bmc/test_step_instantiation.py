"""Building later steps from a template gives exactly the formula lowering gives."""

from __future__ import annotations

import warnings

import pytest

from pyfcstm.bmc import BmcOptions, build_bmc_core_formula, compile_bmc_query
from pyfcstm.bmc.engine import BmcEngine
from pyfcstm.bmc.step_template import MODE_VARIABLE
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

FLAT_MODEL = """
def int x = 0;
def int y = 0;
input int d;
state Root {
    state A { during { x = x + d; y = y + 2 * x - 1; } }
    state B { enter { y = 0; } }
    state C;
    [*] -> A;
    A -> B : if [x >= 2 && y >= 3];
    A -> C :: Stop;
    B -> A :: Back effect { x = 0; };
    B -> [*] : if [y > 100];
}
"""
REGION_MODEL = """
def int x = 0;
def int y = 0;
state Root {
    region First {
        [*] -> Idle;
        state Idle;
        state Busy { during { x = x + 1; } }
        Idle -> Busy :: Go;
        Busy -> Idle : if [x >= 3];
    }
    region Second {
        [*] -> Off;
        state Off;
        state On { during { y = y + x; } }
        Off -> On : if [x >= 1];
        On -> Off : if [y >= 5];
    }
}
"""
NESTED_MODEL = """
def int x = 0;
state Root {
    state Outer {
        state Low { during { x = x + 1; } }
        state High;
        [*] -> Low;
        Low -> High : if [x >= 3];
        High -> Low : if [x >= 9];
        during before { x = x + 1; }
    }
    state Done;
    [*] -> Outer;
    Outer -> Done :: Finish;
}
"""
THREE_REGION_MODEL = """
def int x = 0;
state Root {
    region One {
        [*] -> A;
        state A { during { x = x + 1; } }
        state B;
        A -> B : if [x >= 2];
        B -> [*] : if [x >= 4];
    }
    region Two {
        [*] -> C;
        state C;
        state D { during { x = x + 2; } }
        C -> D : if [x >= 1];
        D -> [*] :: Stop;
    }
    region Three {
        [*] -> Early;
        state Early;
        state Late;
        Early -> Late : if [x >= 3];
        Late -> [*] : if [x >= 6];
    }
}
"""
NO_VARIABLE_REGION_MODEL = """
state Root {
    region One {
        [*] -> A;
        state A;
        state B;
        A -> B :: Go;
        B -> A :: Back;
    }
    region Two {
        [*] -> C;
        state C;
        state D;
        C -> D :: Go;
        D -> C :: Back;
    }
}
"""
REGION_POWER_MODEL = """
def int x = 2;
def int y = 3;
state Root {
    region One { [*] -> A; state A { during { x = x ** y; } } state B; A -> B : if [x > 50]; }
    region Two { [*] -> C; state C; state D; C -> D :: Go; }
}
"""
POWER_MODEL = """
def int x = 2;
def int y = 3;
state Root {
    state A { during { x = x ** y; } }
    state B;
    [*] -> A;
    A -> B : if [x > 100];
}
"""
QUERIES = [
    'check reach <= %d: active("Root.B");',
    "check invariant <= %d: x >= 0;",
    "check forbid <= %d: x < 0;",
]
REGION_QUERIES = [
    'check reach <= %d: active("Root.Second.On");',
    "check invariant <= %d: x >= 0;",
]
THREE_REGION_QUERIES = [
    "check reach <= %d: terminated();",
    "check invariant <= %d: x >= 0;",
]
NO_VARIABLE_QUERIES = ['check reach <= %d: active("Root.Two.D");']


def _compile(model_text, query_text, **options):
    model = load_state_machine_from_text(model_text)
    return compile_bmc_query(
        model, query_text, options=BmcOptions(**options) if options else None
    )


def _canonical(model_text, query_text, mode, monkeypatch, **options):
    monkeypatch.setenv(MODE_VARIABLE, mode)
    formula = _compile(model_text, query_text, **options)
    return formula.core.to_canonical(), formula.solve_formula.sexpr()


@pytest.mark.parametrize("bound", [1, 2, 3, 4, 7, 12])
@pytest.mark.parametrize(
    ("model_text", "queries", "options"),
    [
        pytest.param(FLAT_MODEL, QUERIES, {}, id="flat"),
        pytest.param(FLAT_MODEL, QUERIES, {"cone_slicing": True}, id="flat-cone"),
        pytest.param(NESTED_MODEL, QUERIES[1:], {}, id="nested"),
        pytest.param(REGION_MODEL, REGION_QUERIES, {}, id="regions"),
        pytest.param(THREE_REGION_MODEL, THREE_REGION_QUERIES, {}, id="three-regions"),
        pytest.param(
            NO_VARIABLE_REGION_MODEL, NO_VARIABLE_QUERIES, {}, id="regions-no-variable"
        ),
    ],
)
def test_every_mode_builds_the_same_formula_and_ledger(
    monkeypatch, model_text, queries, options, bound
) -> None:
    for template in queries:
        query = template % bound
        lowered = _canonical(model_text, query, "off", monkeypatch, **options)
        for mode in ("on", "verify"):
            assert (
                _canonical(model_text, query, mode, monkeypatch, **options) == lowered
            )


@pytest.mark.parametrize("bound", [2, 4, 7])
@pytest.mark.parametrize(
    ("model_text", "query"),
    [
        pytest.param(POWER_MODEL, 'check reach <= %d: active("Root.B");', id="flat"),
        pytest.param(
            REGION_POWER_MODEL, 'check reach <= %d: active("Root.One.B");', id="regions"
        ),
    ],
)
def test_instantiated_steps_raise_every_warning_a_lowered_step_raises(
    monkeypatch, model_text, query, bound
) -> None:
    counts = {}
    for mode in ("off", "on", "verify"):
        monkeypatch.setenv(MODE_VARIABLE, mode)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _compile(model_text, query % bound)
        counts[mode] = sorted(str(item.message) for item in caught)

    assert counts["on"] == counts["off"] == counts["verify"]
    assert len(counts["off"]) >= bound


def test_the_option_does_not_change_what_a_prepared_context_builds(
    monkeypatch,
) -> None:
    model = load_state_machine_from_text(FLAT_MODEL)
    context = BmcEngine(model).prepare('check reach <= 6: active("Root.B");')
    monkeypatch.setenv(MODE_VARIABLE, "off")
    lowered = build_bmc_core_formula(context).to_canonical()
    monkeypatch.setenv(MODE_VARIABLE, "on")

    assert build_bmc_core_formula(context).to_canonical() == lowered
