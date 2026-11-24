"""Which shared semantic fixtures the native C-family runners execute."""

import pytest

from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template
from test.testings.native_semantic_alignment import (
    NATIVE_TEMPLATE_NAMES,
    iter_native_semantic_cases,
)
from test.testings.simulate_semantics import iter_semantic_cases

pytestmark = pytest.mark.unittest


def _ids(cases):
    return [case.id for case in cases]


@pytest.mark.parametrize("template_name", NATIVE_TEMPLATE_NAMES)
def test_template_without_the_region_feature_skips_every_region_case(template_name):
    selected = iter_native_semantic_cases(template_name, features=frozenset())
    expected = [
        case
        for case in iter_semantic_cases(runners=["generated_python_alignment"])
        if "regions" not in case.data["categories"]
    ]
    assert sorted(_ids(selected)) == sorted(_ids(expected))
    assert not [case for case in selected if "regions" in case.data["categories"]]


@pytest.mark.parametrize("template_name", NATIVE_TEMPLATE_NAMES)
def test_template_with_the_region_feature_runs_every_region_case(template_name):
    selected = iter_native_semantic_cases(
        template_name, features=frozenset({"region"})
    )
    region_cases = iter_semantic_cases(categories=["regions"])
    assert region_cases, "the corpus is expected to contain region cases"
    assert set(_ids(region_cases)) <= set(_ids(selected))
    assert _ids(selected) == sorted(set(_ids(selected)))
    without = iter_native_semantic_cases(template_name, features=frozenset())
    assert set(_ids(selected)) == set(_ids(without)) | set(_ids(region_cases))


@pytest.mark.parametrize("template_name", NATIVE_TEMPLATE_NAMES)
def test_selection_follows_what_the_packaged_template_declares(template_name, tmp_path):
    renderer = StateMachineCodeRenderer(extract_template(template_name, str(tmp_path)))
    assert _ids(iter_native_semantic_cases(template_name)) == _ids(
        iter_native_semantic_cases(template_name, features=renderer.features)
    )


def test_unknown_template_name_is_rejected():
    with pytest.raises(ValueError, match="unknown native template"):
        iter_native_semantic_cases("python")
