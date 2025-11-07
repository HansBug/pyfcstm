import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import *


@pytest.mark.unittest
class TestModelModelDLC5:
    def test_non_leaf_pseudo_state(self):
        ast_node = parse_with_grammar_entry("""
        def int a = 0;
        def int b = 2;
        state LX {
            state LX1 {
                >> during before {
                    a = b + a * 2;
                    b = a + 2;
                }
            }
            state LX2;
            
            pseudo state LX3 {
                [*] -> LX31;
                state LX31;
                state LX32;
            }

            [*] -> LX1 : if [a == 0];
            LX1 -> [*] effect {
                a = b + 3;
                b = a * (b + 2);
            };
            LX1 -> LX1 : LX2.E2;
        }
        """, entry_name='state_machine_dsl')

        with pytest.raises(SyntaxError) as ei:
            parse_dsl_node_to_state_machine(ast_node)

        err = ei.value
        assert isinstance(err, SyntaxError)
        assert "Pseudo state LX.LX3 must be a leaf state:" in err.msg
        assert "pseudo state LX3 {" in err.msg
