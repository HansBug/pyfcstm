import pytest

from tools.generate_spec import HIDDEN_IMPORTS, generate_spec


@pytest.mark.unittest
def test_python_template_dynamic_filter_is_hidden_imported():
    spec_content, _ = generate_spec(icon_dir='build/icons')

    assert 'pyfcstm.template._python_format' in HIDDEN_IMPORTS
    assert 'pyfcstm.template._python_format' in spec_content
