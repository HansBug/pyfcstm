import pathlib

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import *
from test.testings import get_testfile


@pytest.fixture()
def demo_model_1():
    dsl_code = pathlib.Path(get_testfile("dlc4_dsl_code.fcstm")).read_text()
    ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.fixture()
def demo_model_1_plantuml():
    plantuml_code = pathlib.Path(get_testfile("dlc4_plantuml.puml")).read_text()
    return plantuml_code


@pytest.mark.unittest
class TestModelModelDLC4:
    def test_plantuml_generation(
        self, demo_model_1, demo_model_1_plantuml, text_aligner
    ):
        text_aligner.assert_equal(
            expect=demo_model_1_plantuml,
            actual=demo_model_1.to_plantuml(),
        )
