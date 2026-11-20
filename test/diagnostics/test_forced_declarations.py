"""What the analyzers report when they are called on a model with forced declarations.

A forced declaration whose source has states inside is carried out by a hidden
variable, relays and gate states in the machine that runs. An analyzer that is
handed the loaded model judges the declaration the way it is written instead:
one copy on every state the declaration applies to, with the guard the author
wrote. ``inspect_model`` has always reported that; the direct calls below must
agree with it.
"""

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.diagnostics.analyzers import (
    collect_combo_warnings,
    collect_const_fold_warnings,
    collect_numeric_warnings,
)
from pyfcstm.diagnostics.analyzers.data_flow import collect_data_flow_warnings
from pyfcstm.model import load_state_machine_from_text

CONSTANT_GUARDS = """
state Root {
    [*] -> P;
    state P { [*] -> a; state a; }
    state Q;
    !P -> Q : if [1 > 2];
    Q -> P : if [2 > 1];
}
"""

DIVISION_IN_THE_GUARD = """
def int x = 0;
state Root {
    [*] -> P;
    state P { [*] -> M; state M { [*] -> a; state a { during { x = x + 1; } } } }
    state Q;
    !P -> Q : if [x / 0 > 1];
    Q -> P : if [x > 1];
}
"""

GUARD_ON_A_VARIABLE_NOTHING_WRITES = """
def int x = 0;
state Root {
    [*] -> P;
    state P { [*] -> M; state M { [*] -> a; state a; } }
    state Q;
    !P -> Q : if [x > 3];
    Q -> P :: Back;
}
"""

COMBO_BESIDE_A_FORCED_DECLARATION = """
def int x = 0;
state Root {
    [*] -> P;
    state P { [*] -> a; state a { during { x = x + 1; } } }
    state Q;
    state R;
    !P -> Q :: Stop;
    P -> R : [2 > 1] + Go;
    Q -> P :: Back;
}
"""


def _lowered(source):
    machine = load_state_machine_from_text(source)
    assert machine.forced_variables == ("__forced_0",)
    return machine


def _reported_by_inspect(machine, codes, keys):
    return [
        (item.code, tuple(item.refs.get(key) for key in keys))
        for item in inspect_model(machine).diagnostics
        if item.code in codes
    ]


def _reported(diagnostics, codes, keys):
    return [
        (item.code, tuple(item.refs.get(key) for key in keys))
        for item in diagnostics
        if item.code in codes
    ]


@pytest.mark.unittest
def test_a_constant_guard_on_a_forced_declaration_is_reported_on_every_copy():
    machine = _lowered(CONSTANT_GUARDS)
    keys = ("from_path", "to_path", "guard_text", "transition_index")
    codes = ("W_GUARD_CONST_FALSE", "W_GUARD_CONST_TRUE")

    found = _reported(collect_const_fold_warnings(machine), codes, keys)

    # The declaration is found on its source and on the state below it, with
    # the guard as written, and the positions count the transitions an author
    # would count. In the machine that runs the declared guard also reads the
    # hidden variable and no longer folds, and a relay moves the positions.
    assert found == [
        ("W_GUARD_CONST_FALSE", ("Root.P", "Root.Q", "1 > 2", 0)),
        ("W_GUARD_CONST_TRUE", ("Root.Q", "Root.P", "2 > 1", 2)),
        ("W_GUARD_CONST_FALSE", ("Root.P.a", "[*]", "1 > 2", 3)),
    ]
    assert sorted(found) == sorted(_reported_by_inspect(machine, codes, keys))


@pytest.mark.unittest
def test_a_numeric_finding_in_a_forced_guard_is_reported_on_every_copy():
    machine = _lowered(DIVISION_IN_THE_GUARD)
    keys = ("expr_text",)
    codes = ("W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",)

    found = _reported(collect_numeric_warnings(machine), codes, keys)

    # P, M and a each carry the declaration as written. The machine that runs
    # keeps the guard on P and on the state it rests in only.
    assert found == [("W_NUMERIC_CONSTANT_DIVISION_BY_ZERO", ("x / 0",))] * 3
    assert found == _reported_by_inspect(machine, codes, keys)


@pytest.mark.unittest
def test_a_forced_guard_on_a_variable_nothing_writes_is_reported_on_every_copy():
    machine = _lowered(GUARD_ON_A_VARIABLE_NOTHING_WRITES)
    keys = ("from_path", "to_path", "guard_vars")
    codes = ("W_GUARD_VARS_NEVER_CHANGE",)
    variables = inspect_model(machine).variables

    found = _reported(collect_data_flow_warnings(variables, machine), codes, keys)

    assert found == [
        ("W_GUARD_VARS_NEVER_CHANGE", ("Root.P", "Root.Q", ["x"])),
        ("W_GUARD_VARS_NEVER_CHANGE", ("Root.P.M", "[*]", ["x"])),
        ("W_GUARD_VARS_NEVER_CHANGE", ("Root.P.M.a", "[*]", ["x"])),
    ]
    assert found == _reported_by_inspect(machine, codes, keys)


@pytest.mark.unittest
def test_a_combo_term_beside_a_forced_declaration_is_judged_as_written():
    machine = _lowered(COMBO_BESIDE_A_FORCED_DECLARATION)
    keys = ("term_index", "term_text")
    codes = ("W_COMBO_GUARD_CONST_TRUE",)

    found = _reported(collect_combo_warnings(machine), codes, keys)

    # P is left through the forced declaration, so in the machine that runs
    # its other transitions give way to the hidden variable and the first
    # combo term is no longer a constant.
    assert found == [("W_COMBO_GUARD_CONST_TRUE", (0, "[2 > 1]"))]
    assert found == _reported_by_inspect(machine, codes, keys)
