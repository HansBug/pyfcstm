"""
Unit tests for Layer 2 (PR-A) extensions to :mod:`pyfcstm.diagnostics.codes`.

These tests cover the schema additions introduced for Layer 2:

* ``severity: info`` plus the ``I_*`` code prefix
* the ``for_llm`` payload required for new Layer 2 codes
* the ``capability`` field reserved for analysis tier gating

PR-A only adds the loader plumbing; the existing 14 ``E_*`` codes are
grandfathered without ``for_llm`` to preserve backward compatibility.
PR-B / PR-C populate ``W_*`` / ``I_*`` codes with required ``for_llm``.
"""

import textwrap

import pytest

from pyfcstm.diagnostics import (
    CodesSchemaError,
    ForLlmSpec,
    load_codes,
)
from pyfcstm.diagnostics.codes import (
    _ALLOWED_CAPABILITIES,
    _ALLOWED_SEVERITIES,
    _SEVERITY_PREFIX,
)


def _write_yaml(tmp_path, body):
    path = tmp_path / 'codes.yaml'
    path.write_text(textwrap.dedent(body), encoding='utf-8')
    return str(path)


@pytest.mark.unittest
class TestInfoSeveritySupport:
    def test_info_present_in_allowed_severities(self):
        assert 'info' in _ALLOWED_SEVERITIES

    def test_info_prefix_mapping(self):
        assert _SEVERITY_PREFIX['info'] == 'I_'

    def test_loader_accepts_info_code(self, tmp_path):
        path = _write_yaml(tmp_path, """
            I_DEMO:
              severity: info
              description: example info-level diagnostic
              refs:
                state_path:
                  type: str
                  required: true
                  description: state path
              for_llm:
                summary: an info-level demo
                recommended_actions: []
                do_not: []
        """)
        registry = load_codes(path)
        assert 'I_DEMO' in registry
        assert registry['I_DEMO'].severity == 'info'

    def test_loader_rejects_info_code_with_wrong_prefix(self, tmp_path):
        path = _write_yaml(tmp_path, """
            X_DEMO:
              severity: info
              description: bad prefix
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
        """)
        with pytest.raises(CodesSchemaError, match="expected prefix 'I_'"):
            load_codes(path)


@pytest.mark.unittest
class TestForLlmField:
    def test_loader_accepts_for_llm(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
              for_llm:
                summary: avoid this
                recommended_actions:
                  - {kind: remove, target: var}
                do_not:
                  - "do not add abstract action"
        """)
        registry = load_codes(path)
        for_llm = registry['W_DEMO'].for_llm
        assert isinstance(for_llm, ForLlmSpec)
        assert for_llm.summary == 'avoid this'
        assert len(for_llm.recommended_actions) == 1
        assert for_llm.recommended_actions[0]['kind'] == 'remove'
        assert for_llm.do_not == ('do not add abstract action',)

    def test_loader_rejects_for_llm_missing_required_keys(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
              for_llm:
                summary: missing other keys
        """)
        with pytest.raises(CodesSchemaError, match="missing required keys"):
            load_codes(path)

    def test_loader_rejects_for_llm_with_non_string_summary(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
              for_llm:
                summary: 42
                recommended_actions: []
                do_not: []
        """)
        with pytest.raises(CodesSchemaError, match="for_llm.summary"):
            load_codes(path)

    def test_loader_rejects_for_llm_with_non_list_do_not(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
              for_llm:
                summary: x
                recommended_actions: []
                do_not: "string-not-list"
        """)
        with pytest.raises(CodesSchemaError, match="for_llm.do_not"):
            load_codes(path)


@pytest.mark.unittest
class TestCapabilityField:
    def test_default_capability_is_pure_static(self, tmp_path):
        path = _write_yaml(tmp_path, """
            E_DEMO:
              severity: error
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
        """)
        registry = load_codes(path)
        assert registry['E_DEMO'].capability == 'pure_static'

    def test_explicit_capability_accepted(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: demo
              capability: const_fold
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
        """)
        registry = load_codes(path)
        assert registry['W_DEMO'].capability == 'const_fold'

    def test_invalid_capability_rejected(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: demo
              capability: handwave
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
        """)
        with pytest.raises(CodesSchemaError, match='invalid capability'):
            load_codes(path)

    def test_allowed_capabilities_include_layer3_reservations(self):
        assert 'requires_solver' in _ALLOWED_CAPABILITIES
        assert 'requires_simulation' in _ALLOWED_CAPABILITIES


@pytest.mark.unittest
class TestExistingErrorCodesStillLoad:
    """The 14 Layer 1 ``E_*`` codes must keep loading without ``for_llm``."""

    def test_layer1_codes_grandfathered(self):
        from pyfcstm.diagnostics import CODE_REGISTRY
        for code, spec in CODE_REGISTRY.items():
            if code.startswith('E_'):
                # PR-A does not require for_llm on Layer 1 codes;
                # nullability preserves backward compat.
                assert spec.for_llm is None or isinstance(spec.for_llm, ForLlmSpec)
