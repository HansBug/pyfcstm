import os.path
import shutil

import pytest
from hbutils.system import TemporaryDirectory

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from ..testings import get_testfile, dir_compare, walk_files


@pytest.fixture()
def sample_model():
    ast_node = parse_with_grammar_entry("""
    def int a = 0;
    def int b = 0x0;
    def int round_count = 0;  // define variables
    state TrafficLight {
        state InService {
            enter {
                a = 0;
                b = 0;
                round_count = 0;
            }

            enter abstract InServiceAbstractEnter /*
                Abstract Operation When Entering State 'InService'
                TODO: Should be Implemented In Generated Code Framework
            */

            // for non-leaf state, either 'before' or 'after' aspect keyword should be used for during block
            during before abstract InServiceBeforeEnterChild /*
                Abstract Operation Before Entering Child States of State 'InService'
                TODO: Should be Implemented In Generated Code Framework
            */

            during after abstract InServiceAfterEnterChild /*
                Abstract Operation After Entering Child States of State 'InService'
                TODO: Should be Implemented In Generated Code Framework
            */

            exit abstract InServiceAbstractExit /*
                Abstract Operation When Leaving State 'InService'
                TODO: Should be Implemented In Generated Code Framework
            */

            state Red {
                during {  // no aspect keywords ('before', 'after') should be used for during block of leaf state
                    a = 0x1 << 2;
                }
            }
            state Yellow;
            state Green;
            [*] -> Red :: Start effect {
                b = 0x1;
            };
            Red -> Green effect {
                b = 0x3;
            };
            Green -> Yellow effect {
                b = 0x2;
            };
            Yellow -> Red : if [a >= 10] effect {
                b = 0x1;
                round_count = round_count + 1;
            };
        }
        state Idle;

        [*] -> InService;
        InService -> Idle :: Maintain;
        Idle -> [*];
    }
    """, entry_name='state_machine_dsl')
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.mark.unittest
class TestRenderRender:
    @pytest.mark.parametrize(['template_name', 'result_name'], [
        ('template_1', 'template_1_result'),
        ('template_1_with_static_file', 'template_1_with_static_file_result'),
        ('template_1_with_ignore', 'template_1_with_ignore_result'),
    ])
    def test_actual_render(self, template_name, result_name, sample_model):
        template_dir = get_testfile(template_name)
        expected_result_dir = get_testfile(result_name)

        renderer = StateMachineCodeRenderer(template_dir)
        with TemporaryDirectory() as td:
            renderer.render(
                model=sample_model,
                output_dir=td,
            )
            dir_compare(expected_result_dir, td)

    @pytest.mark.parametrize(['template_name', 'result_name'], [
        ('template_1', 'template_1_result'),
        ('template_1_with_static_file', 'template_1_with_static_file_result'),
        ('template_1_with_ignore', 'template_1_with_ignore_result'),
    ])
    def test_actual_render_with_clear(self, template_name, result_name, sample_model):
        template_dir = get_testfile(template_name)
        expected_result_dir = get_testfile(result_name)

        renderer = StateMachineCodeRenderer(template_dir)
        with TemporaryDirectory() as td:
            for file in walk_files(get_testfile('.')):
                dst_file = os.path.join(td, file)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copyfile(get_testfile(file), dst_file)
            renderer.render(
                model=sample_model,
                output_dir=td,
                clear_previous_directory=True,
            )
            dir_compare(expected_result_dir, td)
