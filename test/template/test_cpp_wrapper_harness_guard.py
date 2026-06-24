"""
Guard C++ fixture harnesses against bypassing wrapper entrypoints.

The tests exercise the lightweight source gate used before generated
``harness.cpp`` files are written for C++ shared semantic fixture alignment.
They keep the fixture runner focused on ``machine.hpp`` wrapper APIs instead
of direct ``machine.h`` C runtime entrypoints.

Example::

    >>> from test.template.cpp_shared import _assert_wrapper_only_harness
    >>> _assert_wrapper_only_harness('#include "machine.hpp"\n')
"""

import pytest

from test.template.cpp_shared import _assert_wrapper_only_harness


@pytest.mark.unittest
def test_cpp_wrapper_harness_accepts_wrapper_entrypoint_only():
    """
    Accept harnesses that include only the C++ wrapper machine header.

    :return: ``None``.
    :rtype: None
    """
    _assert_wrapper_only_harness(
        '#include "machine.hpp"\n'
        "#include <stdio.h>\n"
        "typedef pyfcstm_generated::Root_cpp::MachineWrapper Wrapper;\n"
        "static void use_wrapper(Wrapper *wrapper) { (void)wrapper->cycle(); }\n"
    )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            '#include "machine.hpp"\n#include "machine.h"\n',
            id="quoted-machine-header",
        ),
        pytest.param(
            '#include "machine.hpp"\n#include <machine.h>\n',
            id="angle-machine-header",
        ),
        pytest.param(
            '#include "machine.hpp"\n#include "./machine.h"\n',
            id="relative-machine-header",
        ),
        pytest.param(
            '#include "machine.hpp"\n#include "generated/machine.h" // direct C header\n',
            id="nested-machine-header-with-comment",
        ),
        pytest.param(
            '#include "machine.hpp"\nRootMachine root;\n',
            id="bare-c-machine-object",
        ),
        pytest.param(
            '#include "machine.hpp"\nRootMachine *root;\n',
            id="bare-c-machine-pointer",
        ),
        pytest.param(
            '#include "machine.hpp"\ntypedef RootMachine Alias;\n',
            id="bare-c-machine-alias",
        ),
        pytest.param(
            '#include "machine.hpp"\nRootMachineVars vars;\n',
            id="c-vars-typedef",
        ),
        pytest.param(
            '#include "machine.hpp"\nRootMachine_cycle(root, events, count);\n',
            id="direct-c-api-call",
        ),
        pytest.param(
            '#include "machine.hpp"\nwrapper.native_handle();\n',
            id="native-handle-access",
        ),
    ],
)
def test_cpp_wrapper_harness_rejects_direct_c_runtime_entrypoints(source):
    """
    Reject harnesses that bypass the C++ wrapper surface.

    :param source: Invalid rendered C++ harness source.
    :type source: str
    :return: ``None``.
    :rtype: None
    """
    with pytest.raises(AssertionError):
        _assert_wrapper_only_harness(source)
