import os.path
import shutil
import textwrap
from tempfile import TemporaryDirectory

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry.dispatch import pyfcstmcli
from test.testings import get_testfile, dir_compare, walk_files


@pytest.fixture()
def input_code_file():
    with TemporaryDirectory() as td:
        code_file = os.path.join(td, 'code.fcstm')
        with open(code_file, 'w') as f:
            print(textwrap.dedent("""
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
    """).strip(), file=f)

        yield code_file


@pytest.mark.unittest
class TestEntryGenerate:
    @pytest.mark.parametrize(['template_name', 'result_name'], [
        ('template_1', 'template_1_result'),
        ('template_1_with_static_file', 'template_1_with_static_file_result'),
        ('template_1_with_ignore', 'template_1_with_ignore_result'),
    ])
    def test_actual_render(self, template_name, result_name, input_code_file):
        template_dir = os.path.abspath(get_testfile(template_name))
        expected_result_dir = os.path.abspath(get_testfile(result_name))

        with TemporaryDirectory() as td:
            result = simulate_entry(pyfcstmcli, [
                'pyfcstm', 'generate', '-i', input_code_file, '-t', template_dir, '-o', td,
            ])
            assert result.exitcode == 0
            dir_compare(expected_result_dir, td)

    @pytest.mark.parametrize(['template_name', 'result_name'], [
        ('template_1', 'template_1_result'),
        ('template_1_with_static_file', 'template_1_with_static_file_result'),
        ('template_1_with_ignore', 'template_1_with_ignore_result'),
    ])
    def test_actual_render_with_clear(self, template_name, result_name, input_code_file):
        template_dir = os.path.abspath(get_testfile(template_name))
        expected_result_dir = os.path.abspath(get_testfile(result_name))

        with TemporaryDirectory() as td:
            for file in walk_files(get_testfile('.')):
                dst_file = os.path.join(td, file)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copyfile(get_testfile(file), dst_file)

            result = simulate_entry(pyfcstmcli, [
                'pyfcstm', 'generate', '-i', input_code_file, '-t', template_dir, '-o', td, '--clear',
            ])
            assert result.exitcode == 0
            dir_compare(expected_result_dir, td)
