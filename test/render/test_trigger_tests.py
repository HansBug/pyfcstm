"""Templates discriminate the single model trigger without legacy fields."""

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.render.env import create_env

pytestmark = pytest.mark.unittest


def test_template_trigger_types():
    model = load_state_machine_from_text('''
        def int x = 1;
        state R {
            state A; state B;
            [*] -> A;
            A -> B :: Go;
            A -> B : if [x > 0];
        }
    ''')
    template = create_env().from_string(
        '{% for t in model.root_state.transitions %}'
        '{{ t.trigger is event_trigger }}/{{ t.trigger is guard_trigger }};'
        '{% endfor %}'
    )
    assert template.render(model=model) == 'False/False;True/False;False/True;'
