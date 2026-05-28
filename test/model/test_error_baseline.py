"""
Baseline error snapshot for ``pyfcstm.model.parse_dsl_node_to_state_machine``.

This test file is part of **PR-0** of the Layer 1 structured-diagnostic
refactor (see issue #103). Its purpose is to lock down the **current**
exception-raising behavior of ``model.py`` so that subsequent PRs (especially
PR-2, which replaces ``raise SyntaxError`` with structured ``ModelDiagnostic``
objects) cannot silently regress the existing error-detection surface.

For each baseline case we assert:

1. The DSL snippet still triggers an exception.
2. The exception type matches what model.py currently raises.
3. The exception message contains the documented substring contract that the
   downstream ``research_ideas`` repository (issue ``research_ideas#12``)
   currently regex-matches.

After PR-2 lands, ``ModelValidationError`` will multi-inherit from
``SyntaxError`` so all the ``SyntaxError`` baseline assertions remain green.
The fixture table itself will then be re-used as the source of truth for
asserting structured ``diagnostic.code`` / ``diagnostic.refs`` in PR-2.

.. note::
   This file deliberately uses **substring** assertions, not exact equality,
   because exact message text is *not* part of the public contract. The
   substring is the minimum stable surface that downstream consumers
   currently depend on.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine


def _parse_and_build(dsl_text: str):
    ast = parse_with_grammar_entry(dsl_text, entry_name='state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


_DUPLICATE_VAR = """
def int x = 0;
def int x = 1;
state Root {
    state A;
}
"""

_UNDEFINED_VAR_IN_GUARD = """
def int x = 0;
state Root {
    state A;
    state B;
    A -> B : if [unknown_var > 0];
}
"""

_UNDEFINED_VAR_IN_EFFECT = """
def int x = 0;
state Root {
    state A;
    state B;
    A -> B effect { unknown_var = 1; };
}
"""

_UNDEFINED_VAR_IN_ENTER = """
def int x = 0;
state Root {
    state A {
        enter { unknown_var = 1; }
    }
}
"""

_DUPLICATE_STATE = """
state Root {
    state A;
    state A;
}
"""

_DUPLICATE_FUNCTION_NAME = """
state Root {
    state A {
        enter Foo { }
        enter Foo { }
    }
}
"""

_LEAF_DURING_WITH_ASPECT = """
state Root {
    state A {
        during before { }
    }
}
"""

_COMPOSITE_DURING_WITHOUT_ASPECT = """
state Root {
    state Outer {
        during { }
        state Inner;
        [*] -> Inner;
    }
    [*] -> Outer;
}
"""

_PSEUDO_NOT_LEAF = """
state Root {
    pseudo state Outer {
        state Inner;
        [*] -> Inner;
    }
}
"""

_UNKNOWN_TO_STATE = """
state Root {
    state A;
    A -> NoSuch;
}
"""

_UNKNOWN_FROM_STATE_FORCED = """
state Root {
    state A;
    state B;
    !NoSuch -> A;
}
"""

_MISSING_ENTRY_TRANSITION_IN_COMPOSITE = """
state Root {
    state Outer {
        state Inner;
    }
}
"""

_NAMED_FUNCTION_REF_NOT_FOUND = """
state Root {
    state A {
        enter ref NoSuch.NoSuch;
    }
}
"""

# (case_id, dsl_text, expected_exc_type, expected_message_substring)
BASELINE_CASES = [
    ('duplicate_var', _DUPLICATE_VAR, SyntaxError, 'Duplicated variable definition'),
    ('undefined_var_guard', _UNDEFINED_VAR_IN_GUARD, SyntaxError, 'unknown_var'),
    ('undefined_var_effect', _UNDEFINED_VAR_IN_EFFECT, SyntaxError, 'unknown_var'),
    ('undefined_var_enter', _UNDEFINED_VAR_IN_ENTER, SyntaxError, 'unknown_var'),
    ('duplicate_state', _DUPLICATE_STATE, SyntaxError, 'Duplicate state name'),
    ('duplicate_function_name', _DUPLICATE_FUNCTION_NAME, SyntaxError, 'Duplicate function name'),
    ('leaf_during_with_aspect', _LEAF_DURING_WITH_ASPECT, SyntaxError, 'during cannot assign aspect'),
    ('composite_during_without_aspect', _COMPOSITE_DURING_WITHOUT_ASPECT, SyntaxError,
     "during must assign aspect"),
    ('pseudo_not_leaf', _PSEUDO_NOT_LEAF, SyntaxError, 'Pseudo state'),
    ('unknown_to_state', _UNKNOWN_TO_STATE, SyntaxError, 'Unknown to state'),
    ('unknown_from_state_forced', _UNKNOWN_FROM_STATE_FORCED, SyntaxError, 'Unknown from state'),
    ('missing_entry_transition_in_composite', _MISSING_ENTRY_TRANSITION_IN_COMPOSITE, SyntaxError,
     'entry transition'),
    ('named_function_ref_not_found', _NAMED_FUNCTION_REF_NOT_FOUND, SyntaxError, 'Cannot find'),
]


@pytest.mark.unittest
@pytest.mark.parametrize(
    'case_id,dsl_text,expected_exc,expected_substr',
    BASELINE_CASES,
    ids=[c[0] for c in BASELINE_CASES],
)
def test_error_baseline_raises_expected_exception(case_id, dsl_text, expected_exc, expected_substr):
    """
    Each baseline DSL snippet must trigger ``expected_exc`` with a message
    containing ``expected_substr``. This is the contract surface that
    downstream consumers regex-match today and that PR-2 must preserve.
    """
    with pytest.raises(expected_exc) as exc_info:
        _parse_and_build(dsl_text)
    assert expected_substr in str(exc_info.value), (
        f"[{case_id}] expected substring {expected_substr!r} in exception message, "
        f"got: {str(exc_info.value)!r}"
    )


@pytest.mark.unittest
def test_error_baseline_table_is_non_empty():
    """Guard against accidental table truncation."""
    assert len(BASELINE_CASES) >= 10
