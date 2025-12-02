import argparse
import os
import pathlib
import re
import textwrap

from hbutils.string import titleize

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine


def _name_safe(name_text):
    return re.sub(r'[\W_]+', '_', name_text).strip('_')


def _name_titleize(name_text):
    return titleize(_name_safe(name_text)).replace('_', '').replace(' ', '')


def _to_ast_node(text: str):
    return re.sub(r'([A-Z][A-Za-z0-9]*|INIT_STATE|EXIT_STATE)\(', r'dsl_nodes.\1(', text)


def get_properties(o):
    ext = []
    for name in dir(type(o)):
        if isinstance(getattr(type(o), name), property):
            ext.append(name)

    return ext


def sample_generation_to_file(code: str, test_file: str):
    code = textwrap.dedent(code).strip()
    ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')

    syntax_error = None
    try:
        _ = parse_dsl_node_to_state_machine(ast_node)
    except SyntaxError as err:
        syntax_error = err
    else:
        assert False, 'Not raise error'

    with open(test_file, 'w') as tf:
        print(f'import textwrap', file=tf)
        print(f'import pytest', file=tf)
        print(f'', file=tf)
        print(f'from pyfcstm.dsl import node as dsl_nodes', file=tf)
        print(f'from pyfcstm.dsl.node import INIT_STATE, EXIT_STATE', file=tf)
        print(f'from pyfcstm.dsl import parse_with_grammar_entry', file=tf)
        print(f'from pyfcstm.model.expr import *', file=tf)
        print(f'from pyfcstm.model.model import *', file=tf)
        print(f'', file=tf)
        print(f'', file=tf)

        print(f'@pytest.fixture()', file=tf)
        print(f'def ast_node():', file=tf)
        print(f'    return parse_with_grammar_entry("""', file=tf)
        print(code, file=tf)
        print(f'    """, entry_name=\'state_machine_dsl\')', file=tf)
        print(f'', file=tf)
        print(f'', file=tf)

        print(f'@pytest.mark.unittest', file=tf)
        print(f'class TestModel{_name_titleize(os.path.splitext(os.path.basename(test_file))[0])}:', file=tf)
        print(f'    def test_parse_dsl_node_to_state_machine(self, ast_node, text_aligner):', file=tf)
        print(f'        with pytest.raises(SyntaxError) as ei:', file=tf)
        print(f'            _ = parse_dsl_node_to_state_machine(ast_node)', file=tf)
        print(f'')
        print(f'        err = ei.value', file=tf)
        print(f'        assert isinstance(err, SyntaxError)', file=tf)
        print(f'        text_aligner.assert_equal(', file=tf)
        print(f'            expect=textwrap.dedent("""', file=tf)
        print(f'{syntax_error.args[0]}', file=tf)
        print(f'            """).strip(),', file=tf)
        print(f'            actual=err.args[0],', file=tf)
        print(f'        )', file=tf)
        print(f'', file=tf)


def main():
    """Main function to parse arguments and update requirements.txt"""
    parser = argparse.ArgumentParser(description='Auto create unittest for file model nodes')
    parser.add_argument('-i', '--input-file', required=True, help='Input pyfcstm code file')
    parser.add_argument('-o', '--output-file', required=True, help='Output unittest code file')
    args = parser.parse_args()

    sample_generation_to_file(
        code=pathlib.Path(args.input_file).read_text(),
        test_file=args.output_file,
    )


if __name__ == "__main__":
    main()
