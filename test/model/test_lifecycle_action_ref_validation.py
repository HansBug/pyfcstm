"""
Lifecycle action reference validation tests.

These tests keep model-construction diagnostics out of the shared semantic
fixture corpus while preserving the original DSL inputs and structured
diagnostic assertions.
"""

import re

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils import ModelValidationError


def _assert_lifecycle_ref_cycle(dsl_code, message, cycle_path):
    ast = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')

    with pytest.raises(ModelValidationError, match=re.escape(message)) as info:
        parse_dsl_node_to_state_machine(ast)

    assert info.value.diagnostics, "expected structured diagnostics"
    diag = info.value.diagnostics[0]
    assert diag.code == 'E_NAMED_FUNCTION_REF_CYCLE'
    assert diag.message == message
    assert isinstance(diag.refs['cycle_path'], str)
    assert diag.refs['cycle_path'] == cycle_path
    assert diag.refs['reason'] == 'action_ref_cycle'


@pytest.mark.unittest
class TestLifecycleActionRefCycleValidation:
    """Validate lifecycle action ``ref`` cycle diagnostics."""

    def test_self_ref_cycle_raises_diagnostic(self):
        """A lifecycle action cannot reference itself."""
        _assert_lifecycle_ref_cycle(
            """
def int x = 0;
state Root {
    enter A ref A;
    state Idle { during { x = x + 1; } }
    [*] -> Idle;
}
""",
            "Action reference cycle: Root.A -> Root.A",
            "Root.A -> Root.A",
        )

    def test_two_node_ref_cycle_raises_diagnostic(self):
        """A two-action lifecycle reference cycle is rejected."""
        _assert_lifecycle_ref_cycle(
            """
def int x = 0;
state Root {
    enter A ref B;
    enter B ref A;
    state Idle { during { x = x + 1; } }
    [*] -> Idle;
}
""",
            "Action reference cycle: Root.A -> Root.B -> Root.A",
            "Root.A -> Root.B -> Root.A",
        )

    def test_multi_node_ref_cycle_raises_diagnostic(self):
        """A longer lifecycle reference cycle is rejected."""
        _assert_lifecycle_ref_cycle(
            """
def int x = 0;
state Root {
    enter A ref B;
    enter B ref C;
    enter C ref A;
    state Idle { during { x = x + 1; } }
    [*] -> Idle;
}
""",
            "Action reference cycle: Root.A -> Root.B -> Root.C -> Root.A",
            "Root.A -> Root.B -> Root.C -> Root.A",
        )
