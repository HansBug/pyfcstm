import textwrap
import pytest

from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl.node import INIT_STATE, EXIT_STATE
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.expr import *
from pyfcstm.model.model import *


@pytest.fixture()
def ast_node():
    return parse_with_grammar_entry(
        """
state L1 {
    [*] -> L21;
    L21 -> L22;

    state L21 {
        enter F1 {}
        during F1 {}
    }
    state L22;
}
    """,
        entry_name="state_machine_dsl",
    )


@pytest.mark.unittest
class TestModelTestSampleNegDlc6F2:
    def test_parse_dsl_node_to_state_machine(self, ast_node, text_aligner):
        with pytest.raises(SyntaxError) as ei:
            _ = parse_dsl_node_to_state_machine(ast_node)
        err = ei.value
        assert isinstance(err, SyntaxError)
        text_aligner.assert_equal(
            expect=textwrap.dedent("""
Duplicate function name 'F1' in state:
state L21 {
    enter F1 {
    }
    during F1 {
    }
}
            """).strip(),
            actual=err.args[0],
        )
