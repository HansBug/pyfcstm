import importlib

import pytest
from hbutils.reflection import quick_import_object

from tools.generate_spec import HIDDEN_IMPORTS, generate_spec


@pytest.mark.unittest
def test_python_template_dynamic_filter_is_hidden_imported():
    import_path = 'pyfcstm.template._python_format'
    filter_path = '%s.clean_python_runtime_source' % import_path

    spec_content, _ = generate_spec(icon_dir='build/icons')
    module = importlib.import_module(import_path)
    filter_object, _, _ = quick_import_object(filter_path)

    assert import_path in HIDDEN_IMPORTS
    assert import_path in spec_content
    assert callable(module.clean_python_runtime_source)
    assert filter_object is module.clean_python_runtime_source
