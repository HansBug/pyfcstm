import argparse
import dataclasses
import pathlib
import re
import textwrap

from hbutils.string import titleize

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine, State


def _name_safe(name_text):
    return re.sub(r'[\W_]+', '_', name_text).strip('_')


def _state_name(state: State):
    return _name_safe(f'state_{"_".join(state.path)}'.lower())


def _state_name_cap(state: State):
    return titleize(_name_safe(f'state_{"_".join(state.path)}')).replace('_', '').replace(' ', '')


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
    model = parse_dsl_node_to_state_machine(ast_node)

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
        print(f'def model():', file=tf)
        print(f'    ast_node = parse_with_grammar_entry("""', file=tf)
        print(code, file=tf)
        print(f'    """, entry_name=\'state_machine_dsl\')', file=tf)
        print(f'    model = parse_dsl_node_to_state_machine(ast_node)', file=tf)
        print(f'    return model', file=tf)
        print(f'', file=tf)
        print(f'', file=tf)

        for state in model.walk_states():
            state: State
            if state is model.root_state:
                print(f'@pytest.fixture()', file=tf)
                print(f'def {_state_name(state)}(model):', file=tf)
                print(f'    return model.root_state', file=tf)
            else:
                print(f'@pytest.fixture()', file=tf)
                print(f'def {_state_name(state)}({_state_name(state.parent)}):', file=tf)
                print(f'    return {_state_name(state.parent)}.substates[{state.name!r}]', file=tf)
            print(f'', file=tf)
            print(f'', file=tf)

        print(f'@pytest.mark.unittest', file=tf)
        print(f'class TestModel{_state_name_cap(model.root_state)}:', file=tf)
        print(f'    def test_model(self, model):', file=tf)
        print(f'        assert model.defines == {model.defines!r}', file=tf)
        print(f'        assert model.root_state.name == {model.root_state.name!r}', file=tf)
        print(f'        assert model.root_state.path == {model.root_state.path!r}', file=tf)
        print(f'', file=tf)

        ast_node = model.to_ast_node()
        print(f'    def test_model_to_ast(self, model):', file=tf)
        print(f'        ast_node = model.to_ast_node()', file=tf)
        # _to_ast_node(repr(ast_node.definitions))
        print(f'        assert ast_node.definitions == {_to_ast_node(repr(ast_node.definitions))}', file=tf)
        print(f'        assert ast_node.root_state.name == {ast_node.root_state.name!r}', file=tf)
        print(f'', file=tf)

        for state in model.walk_states():
            state: State
            print(f'    def test_{_state_name(state)}(self, {_state_name(state)}):', file=tf)
            # for field in dataclasses.fields(state):
            for field_name in [
                *map(lambda x: x.name, dataclasses.fields(state)),
                *get_properties(state),
            ]:
                obj = getattr(state, field_name)

                if obj is None:
                    print(f'        assert {_state_name(state)}.{field_name} is None', file=tf)
                elif isinstance(obj, bool):
                    if obj:
                        print(f'        assert {_state_name(state)}.{field_name}', file=tf)
                    else:
                        print(f'        assert not {_state_name(state)}.{field_name}', file=tf)
                elif field_name == 'parent_ref':
                    print(f'        assert {_state_name(state)}.{field_name}().name == {obj().name!r}', file=tf)
                    print(f'        assert {_state_name(state)}.{field_name}().path == {obj().path!r}', file=tf)
                elif field_name == 'parent':
                    print(f'        assert {_state_name(state)}.{field_name}.name == {obj.name!r}', file=tf)
                    print(f'        assert {_state_name(state)}.{field_name}.path == {obj.path!r}', file=tf)
                elif field_name == 'substates':
                    print(f'        assert set({_state_name(state)}.{field_name}.keys()) == {set(obj.keys())!r}',
                          file=tf)
                elif (field_name == 'transitions' or field_name.startswith('transitions_')) and obj:
                    print(f'        assert len({_state_name(state)}.{field_name}) == {len(obj)!r}', file=tf)
                    # print(f'        assert {_state_name(state)}.{field_name} == {obj!r}', file=tf)
                    for j, transition in enumerate(obj):
                        if transition:
                            for f in dataclasses.fields(transition):
                                if getattr(transition, f.name) is None:
                                    print(f'        assert {_state_name(state)}.{field_name}[{j}].{f.name} is None',
                                          file=tf)
                                elif f.name == 'parent_ref':
                                    print(
                                        f'        assert {_state_name(state)}.{field_name}[{j}].{f.name}().name == {getattr(transition, f.name)().name!r}',
                                        file=tf)
                                    print(
                                        f'        assert {_state_name(state)}.{field_name}[{j}].{f.name}().path == {getattr(transition, f.name)().path!r}',
                                        file=tf)
                                else:
                                    print(
                                        f'        assert {_state_name(state)}.{field_name}[{j}].{f.name} == {getattr(transition, f.name)!r}',
                                        file=tf)
                        else:
                            print(f'        assert {_state_name(state)}.{field_name}[{j}] is None', file=tf)

                else:
                    print(f'        assert {_state_name(state)}.{field_name} == {obj!r}', file=tf)
            print(f'', file=tf)

            ast_node = state.to_ast_node()
            print(f'    def test_{_state_name(state)}_to_ast_node(self, {_state_name(state)}):', file=tf)
            print(f'        ast_node = {_state_name(state)}.to_ast_node()', file=tf)
            print(f'        assert ast_node == {_to_ast_node(repr(ast_node))}', file=tf)
            print(f'', file=tf)

        print(f'    def test_to_ast_node_str(self, model, text_aligner):', file=tf)
        print(f'        text_aligner.assert_equal(', file=tf)
        print(f'            expect=textwrap.dedent("""', file=tf)
        repr_code = str(model.to_ast_node())
        print(f'{repr_code}', file=tf)
        print(f'            """).strip(),', file=tf)
        print(f'            actual=str(model.to_ast_node()),', file=tf)
        print(f'        )', file=tf)

        print(f'    def test_to_plantuml(self, model, text_aligner):', file=tf)
        print(f'        text_aligner.assert_equal(', file=tf)
        print(f'            expect=textwrap.dedent("""', file=tf)
        repr_code = model.to_plantuml().replace("\\", "\\\\")
        print(f'{repr_code}', file=tf)
        print(f'            """).strip(),', file=tf)
        print(f'            actual=str(model.to_plantuml()),', file=tf)
        print(f'        )', file=tf)


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
