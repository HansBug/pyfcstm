import argparse
import dataclasses
import pathlib
import re
import textwrap

from hbutils.reflection import nested_for
from hbutils.string import titleize

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine, State, OnStage, OnAspect


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
                    print(f'        assert sorted({_state_name(state)}.{field_name}.keys()) == {sorted(obj.keys())!r}',
                          file=tf)
                elif (field_name == 'transitions' or field_name.startswith('transitions_') or field_name.endswith(
                        '_transitions')) and obj:
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
                elif obj and isinstance(obj, dict) and isinstance(list(obj.values())[0], (OnStage, OnAspect)):
                    print(f'        assert sorted({_state_name(state)}.{field_name}.keys()) == {sorted(obj.keys())}',
                          file=tf)
                    for oskey, obj_item in obj.items():
                        for os_field_name in [
                            *map(lambda x: x.name, dataclasses.fields(obj_item)),
                            *get_properties(obj_item),
                        ]:
                            obj_item_v = getattr(obj_item, os_field_name)
                            if isinstance(obj_item_v, type(None)):
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name} is None',
                                    file=tf)
                            elif isinstance(obj_item_v, bool):
                                if obj_item_v:
                                    print(
                                        f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}',
                                        file=tf)
                                else:
                                    print(
                                        f'        assert not {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}',
                                        file=tf)
                            elif os_field_name == 'parent':
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}.name == {obj_item_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}.path == {obj_item_v.path!r}',
                                    file=tf)
                            elif os_field_name == 'parent_ref':
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}().name == {obj_item_v().name!r}',
                                    file=tf)
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}().path == {obj_item_v().path!r}',
                                    file=tf)
                            elif os_field_name == 'ref':
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}.name == {obj_item_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}.aspect == {obj_item_v.aspect!r}',
                                    file=tf)
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name}.state_path == {obj_item_v.state_path!r}',
                                    file=tf)
                            else:
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{oskey!r}].{os_field_name} == {obj_item_v!r}',
                                    file=tf)

                elif obj and isinstance(obj, (list, tuple)) and isinstance(obj[0], (OnStage, OnAspect)):
                    print(f'        assert len({_state_name(state)}.{field_name}) == {len(obj)}', file=tf)
                    for osi, obj_item in enumerate(obj):
                        for os_field_name in [
                            *map(lambda x: x.name, dataclasses.fields(obj_item)),
                            *get_properties(obj_item),
                        ]:
                            obj_item_v = getattr(obj_item, os_field_name)
                            if isinstance(obj_item_v, type(None)):
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name} is None',
                                    file=tf)
                            elif isinstance(obj_item_v, bool):
                                if obj_item_v:
                                    print(f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name}',
                                          file=tf)
                                else:
                                    print(
                                        f'        assert not {_state_name(state)}.{field_name}[{osi}].{os_field_name}',
                                        file=tf)
                            elif os_field_name == 'parent':
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name}.name == {obj_item_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name}.path == {obj_item_v.path!r}',
                                    file=tf)
                            elif os_field_name == 'parent_ref':
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name}().name == {obj_item_v().name!r}',
                                    file=tf)
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name}().path == {obj_item_v().path!r}',
                                    file=tf)
                            elif os_field_name == 'ref':
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name}.name == {obj_item_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name}.aspect == {obj_item_v.aspect!r}',
                                    file=tf)
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name}.state_path == {obj_item_v.state_path!r}',
                                    file=tf)
                            else:
                                print(
                                    f'        assert {_state_name(state)}.{field_name}[{osi}].{os_field_name} == {obj_item_v!r}',
                                    file=tf)
                else:
                    print(f'        assert {_state_name(state)}.{field_name} == {obj!r}', file=tf)
            print(f'', file=tf)

            ast_node = state.to_ast_node()
            print(f'    def test_{_state_name(state)}_to_ast_node(self, {_state_name(state)}):', file=tf)
            print(f'        ast_node = {_state_name(state)}.to_ast_node()', file=tf)
            print(f'        assert ast_node == {_to_ast_node(repr(ast_node))}', file=tf)
            print(f'', file=tf)

            print(f'    def test_{_state_name(state)}_list_on_enters(self, {_state_name(state)}):', file=tf)
            for is_abstract, with_ids in nested_for([None, False, True], [None, False, True]):
                if is_abstract is not None and with_ids is not None:
                    print(
                        f'        lst = {_state_name(state)}.list_on_enters(is_abstract={is_abstract!r}, with_ids={with_ids!r})',
                        file=tf)
                elif is_abstract is not None:
                    print(
                        f'        lst = {_state_name(state)}.list_on_enters(is_abstract={is_abstract!r})',
                        file=tf)
                elif with_ids is not None:
                    print(
                        f'        lst = {_state_name(state)}.list_on_enters(with_ids={with_ids!r})', file=tf)
                else:
                    print(f'        lst = {_state_name(state)}.list_on_enters()', file=tf)

                lst = state.list_on_enters(is_abstract=is_abstract, with_ids=with_ids)
                if not lst:
                    print(f'        assert lst == {lst!r}', file=tf)
                else:
                    print(f'        assert len(lst) == {len(lst)!r}', file=tf)
                    for lst_item_id, lst_item in enumerate(lst):
                        if isinstance(lst_item, tuple):
                            id_, on_stage = lst_item
                            print(f'        id_, on_stage = lst[{lst_item_id!r}]', file=tf)
                            print(f'        assert id_ == {id_!r}', file=tf)
                        else:
                            on_stage = lst_item
                            print(f'        on_stage = lst[{lst_item_id!r}]', file=tf)

                        for os_field_name in [
                            *map(lambda x: x.name, dataclasses.fields(on_stage)),
                            *get_properties(on_stage),
                        ]:
                            on_stage_v = getattr(on_stage, os_field_name)
                            if isinstance(on_stage_v, type(None)):
                                print(
                                    f'        assert on_stage.{os_field_name} is None',
                                    file=tf)
                            elif isinstance(on_stage_v, bool):
                                if on_stage_v:
                                    print(f'        assert on_stage.{os_field_name}',
                                          file=tf)
                                else:
                                    print(
                                        f'        assert not on_stage.{os_field_name}',
                                        file=tf)
                            elif os_field_name == 'parent':
                                print(
                                    f'        assert on_stage.{os_field_name}.name == {on_stage_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.path == {on_stage_v.path!r}',
                                    file=tf)
                            elif os_field_name == 'parent_ref':
                                print(
                                    f'        assert on_stage.{os_field_name}().name == {on_stage_v().name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}().path == {on_stage_v().path!r}',
                                    file=tf)
                            elif os_field_name == 'ref':
                                print(
                                    f'        assert on_stage.{os_field_name}.name == {on_stage_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.aspect == {on_stage_v.aspect!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.state_path == {on_stage_v.state_path!r}',
                                    file=tf)
                            else:
                                print(
                                    f'        assert on_stage.{os_field_name} == {on_stage_v!r}',
                                    file=tf)

                print(f'', file=tf)

            print(f'    def test_{_state_name(state)}_during_aspects(self, {_state_name(state)}):',
                  file=tf)
            for is_abstract, aspect in nested_for([None, False, True], [None, 'before', 'after']):
                if is_abstract is not None and aspect is not None:
                    print(
                        f'        lst = {_state_name(state)}.list_on_during_aspects(is_abstract={is_abstract!r}, aspect={aspect!r})',
                        file=tf)
                elif is_abstract is not None:
                    print(
                        f'        lst = {_state_name(state)}.list_on_during_aspects(is_abstract={is_abstract!r})',
                        file=tf)
                elif aspect is not None:
                    print(
                        f'        lst = {_state_name(state)}.list_on_during_aspects(aspect={aspect!r})', file=tf)
                else:
                    print(f'        lst = {_state_name(state)}.list_on_during_aspects()', file=tf)
                lst = state.list_on_during_aspects(is_abstract=is_abstract, aspect=aspect)
                if not lst:
                    print(f'        assert lst == {lst!r}', file=tf)
                else:
                    print(f'        assert len(lst) == {len(lst)!r}', file=tf)
                    for j, lst_item in enumerate(lst):
                        on_stage = lst_item
                        print(f'        on_stage = lst[{j!r}]', file=tf)
                        # print(f'        assert st.name == {st.name!r}', file=tf)
                        # print(f'        assert st.path == {st.path!r}', file=tf)
                        # print(f'        assert on_stage == {on_stage!r}', file=tf)
                        for os_field_name in [
                            *map(lambda x: x.name, dataclasses.fields(on_stage)),
                            *get_properties(on_stage),
                        ]:
                            on_stage_v = getattr(on_stage, os_field_name)
                            if isinstance(on_stage_v, type(None)):
                                print(
                                    f'        assert on_stage.{os_field_name} is None',
                                    file=tf)
                            elif isinstance(on_stage_v, bool):
                                if on_stage_v:
                                    print(f'        assert on_stage.{os_field_name}',
                                          file=tf)
                                else:
                                    print(
                                        f'        assert not on_stage.{os_field_name}',
                                        file=tf)
                            elif os_field_name == 'parent':
                                print(
                                    f'        assert on_stage.{os_field_name}.name == {on_stage_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.path == {on_stage_v.path!r}',
                                    file=tf)
                            elif os_field_name == 'parent_ref':
                                print(
                                    f'        assert on_stage.{os_field_name}().name == {on_stage_v().name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}().path == {on_stage_v().path!r}',
                                    file=tf)
                            elif os_field_name == 'ref':
                                print(
                                    f'        assert on_stage.{os_field_name}.name == {on_stage_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.aspect == {on_stage_v.aspect!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.state_path == {on_stage_v.state_path!r}',
                                    file=tf)
                            else:
                                print(
                                    f'        assert on_stage.{os_field_name} == {on_stage_v!r}',
                                    file=tf)

                print(f'', file=tf)

            if state.is_leaf_state:
                print(f'    def test_{_state_name(state)}_during_aspect_recursively(self, {_state_name(state)}):',
                      file=tf)

                print(f'        lst = {_state_name(state)}.list_on_during_aspect_recursively()', file=tf)
                lst = state.list_on_during_aspect_recursively()
                if not lst:
                    print(f'        assert lst == {lst!r}', file=tf)
                else:
                    print(f'        assert len(lst) == {len(lst)!r}', file=tf)
                    for j, lst_item in enumerate(lst):
                        st, on_stage = lst_item
                        print(f'        st, on_stage = lst[{j!r}]', file=tf)
                        print(f'        assert st.name == {st.name!r}', file=tf)
                        print(f'        assert st.path == {st.path!r}', file=tf)
                        # print(f'        assert on_stage == {on_stage!r}', file=tf)
                        for os_field_name in [
                            *map(lambda x: x.name, dataclasses.fields(on_stage)),
                            *get_properties(on_stage),
                        ]:
                            on_stage_v = getattr(on_stage, os_field_name)
                            if isinstance(on_stage_v, type(None)):
                                print(
                                    f'        assert on_stage.{os_field_name} is None',
                                    file=tf)
                            elif isinstance(on_stage_v, bool):
                                if on_stage_v:
                                    print(f'        assert on_stage.{os_field_name}',
                                          file=tf)
                                else:
                                    print(
                                        f'        assert not on_stage.{os_field_name}',
                                        file=tf)
                            elif os_field_name == 'parent':
                                print(
                                    f'        assert on_stage.{os_field_name}.name == {on_stage_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.path == {on_stage_v.path!r}',
                                    file=tf)
                            elif os_field_name == 'parent_ref':
                                print(
                                    f'        assert on_stage.{os_field_name}().name == {on_stage_v().name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}().path == {on_stage_v().path!r}',
                                    file=tf)
                            elif os_field_name == 'ref':
                                print(
                                    f'        assert on_stage.{os_field_name}.name == {on_stage_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.aspect == {on_stage_v.aspect!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.state_path == {on_stage_v.state_path!r}',
                                    file=tf)
                            else:
                                print(
                                    f'        assert on_stage.{os_field_name} == {on_stage_v!r}',
                                    file=tf)

                print(f'', file=tf)

                print(f'        lst = {_state_name(state)}.list_on_during_aspect_recursively(with_ids=True)', file=tf)
                lst = state.list_on_during_aspect_recursively(with_ids=True)
                if not lst:
                    print(f'        assert lst == {lst!r}', file=tf)
                else:
                    print(f'        assert len(lst) == {len(lst)!r}', file=tf)
                    for j, lst_item in enumerate(lst):
                        id_, st, on_stage = lst_item
                        print(f'        id_, st, on_stage = lst[{j!r}]', file=tf)
                        print(f'        assert id_ == {id_!r}', file=tf)
                        print(f'        assert st.name == {st.name!r}', file=tf)
                        print(f'        assert st.path == {st.path!r}', file=tf)
                        # print(f'        assert on_stage == {on_stage!r}', file=tf)
                        for os_field_name in [
                            *map(lambda x: x.name, dataclasses.fields(on_stage)),
                            *get_properties(on_stage),
                        ]:
                            on_stage_v = getattr(on_stage, os_field_name)
                            if isinstance(on_stage_v, type(None)):
                                print(
                                    f'        assert on_stage.{os_field_name} is None',
                                    file=tf)
                            elif isinstance(on_stage_v, bool):
                                if on_stage_v:
                                    print(f'        assert on_stage.{os_field_name}',
                                          file=tf)
                                else:
                                    print(
                                        f'        assert not on_stage.{os_field_name}',
                                        file=tf)
                            elif os_field_name == 'parent':
                                print(
                                    f'        assert on_stage.{os_field_name}.name == {on_stage_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.path == {on_stage_v.path!r}',
                                    file=tf)
                            elif os_field_name == 'parent_ref':
                                print(
                                    f'        assert on_stage.{os_field_name}().name == {on_stage_v().name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}().path == {on_stage_v().path!r}',
                                    file=tf)
                            elif os_field_name == 'ref':
                                print(
                                    f'        assert on_stage.{os_field_name}.name == {on_stage_v.name!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.aspect == {on_stage_v.aspect!r}',
                                    file=tf)
                                print(
                                    f'        assert on_stage.{os_field_name}.state_path == {on_stage_v.state_path!r}',
                                    file=tf)
                            else:
                                print(
                                    f'        assert on_stage.{os_field_name} == {on_stage_v!r}',
                                    file=tf)

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
