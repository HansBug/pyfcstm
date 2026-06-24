"""
Guard C++ fixture harnesses against bypassing wrapper entrypoints.

The tests exercise the lightweight source gate used before generated
``harness.cpp`` files are written for C++ shared semantic fixture alignment.
They keep the fixture runner focused on ``machine.hpp`` wrapper APIs instead
of direct ``machine.h`` C runtime entrypoints. This is a closed regression
corpus for fixture harness discipline, not a full C++ static analyzer.

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
        "// native_handle and RootMachine_cycle are diagnostic words only.\n"
        'const char *diagnostic = "RootMachine_cycle";\n'
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
            '#include "machine.hpp"\n#include"machine.h"\n',
            id="quoted-machine-header-without-space",
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
            '#include "machine.hpp"\n#include "MACHINE.H"\n',
            id="case-variant-machine-header",
        ),
        pytest.param(
            '#include "machine.hpp"\n/* temporary */ #include "machine.h"\n',
            id="block-comment-prefix-machine-header",
        ),
        pytest.param(
            '#include "machine.hpp"\n#define HEADER "machine.h"\n#include HEADER\n',
            id="macro-indirect-machine-header",
        ),
        pytest.param(
            '#include "machine.hpp"\n#\\\ninclude "machine.h"\n',
            id="line-continued-include-directive",
        ),
        pytest.param(
            '#include "machine.hpp"\n#include "machine.\\\nh"\n',
            id="line-continued-machine-header-name",
        ),
        pytest.param(
            '#include "machine.hpp"\n#include "machine" ".h"\n',
            id="split-machine-header-string-tokens",
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
            '#include "machine.hpp"\nvoid (*fn)(void) = &RootMachine_cycle;\n',
            id="direct-c-api-address",
        ),
        pytest.param(
            '#include "machine.hpp"\n#define C_API(name) RootMachine_##name\nC_API(cycle)(root, events, count);\n',
            id="token-paste-c-api-suffix",
        ),
        pytest.param(
            '#include "machine.hpp"\n#define CYCLE RootMachine_cycle\nCYCLE(root, events, count);\n',
            id="macro-alias-c-api-token",
        ),
        pytest.param(
            '#include "machine.hpp"\nRootMachine_\\\ncycle(root, events, count);\n',
            id="line-continued-c-api-token",
        ),
        pytest.param(
            '#include "machine.hpp"\n#define CALL(name) name##Machine_cycle(0, 0, 0)\nCALL(Root);\n',
            id="token-paste-c-api-prefix",
        ),
        pytest.param(
            '#include "machine.hpp"\nwrapper.native_handle();\n',
            id="native-handle-access",
        ),
        pytest.param(
            '// #include "machine.hpp"\nstatic void use_wrapper(void) {}\n',
            id="commented-wrapper-header-only",
        ),
        pytest.param(
            'const char *header = "machine.hpp";\nstatic void use_wrapper(void) {}\n',
            id="string-literal-wrapper-header-only",
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
