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
class TestEmitTierField:
    def test_loader_accepts_catalog_only_emit_tier(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: catalog-only demo
              capability: pure_static
              emit_tier: catalog_only
              refs:
                expr_text:
                  type: str
                  required: true
                  description: expression
            """)
        registry = load_codes(path)
        assert registry['W_DEMO'].emit_tier == 'catalog_only'

    def test_loader_accepts_list_string_item_contracts(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: list string schema demo
              refs:
                target_templates:
                  type: list[str]
                  required: true
                  description: target template set
                  item_enum: [c, c_poll]
                  exact_values: [c, c_poll]
            """)
        spec = load_codes(path)['W_DEMO'].refs_schema['target_templates']
        assert spec.item_enum == ('c', 'c_poll')
        assert spec.exact_values == ('c', 'c_poll')

    def test_loader_rejects_list_contracts_on_scalar_types(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: bad list schema demo
              refs:
                target_family:
                  type: str
                  required: true
                  description: target family
                  item_enum: [c_family]
            """)
        with pytest.raises(CodesSchemaError, match='item_enum'):
            load_codes(path)

    def test_loader_rejects_exact_values_outside_item_enum(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: bad exact list schema demo
              refs:
                target_templates:
                  type: list[str]
                  required: true
                  description: target templates
                  item_enum: [c, c_poll]
                  exact_values: [c, python]
            """)
        with pytest.raises(CodesSchemaError, match='exact_values'):
            load_codes(path)


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


@pytest.mark.unittest
class TestCodesLoaderNegativePaths:
    """Coverage for the schema-validation error branches in
    ``pyfcstm.diagnostics.codes``. Per the PR #115 codecov comment,
    several loader error paths had no test coverage; this class fills
    them in so each ``raise CodesSchemaError`` site is exercised.
    """

    def test_loader_rejects_invalid_emit_tier(self, tmp_path):
        path = _write_yaml(tmp_path, """
            E_DEMO:
              severity: error
              description: demo
              emit_tier: junk_tier
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
            """)
        with pytest.raises(CodesSchemaError, match='invalid emit_tier'):
            load_codes(path)

    def test_loader_accepts_verify_pipeline_emit_tier(self, tmp_path):
        path = _write_yaml(tmp_path, """
            W_DEMO:
              severity: warning
              description: verify-only demo
              capability: requires_solver
              emit_tier: verify_pipeline
              refs:
                algorithm_name:
                  type: str
                  required: true
                  description: algorithm
            """)
        registry = load_codes(path)
        assert registry['W_DEMO'].emit_tier == 'verify_pipeline'

    def test_loader_rejects_for_llm_not_a_dict(self, tmp_path):
        # ``for_llm`` declared as a string — must be a mapping.
        path = _write_yaml(tmp_path, """
            E_DEMO:
              severity: error
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
              for_llm: "not a dict"
            """)
        with pytest.raises(CodesSchemaError, match="'for_llm' must be a mapping"):
            load_codes(path)

    def test_loader_rejects_for_llm_recommended_actions_not_a_list(self, tmp_path):
        path = _write_yaml(tmp_path, """
            E_DEMO:
              severity: error
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
              for_llm:
                summary: short
                recommended_actions: "not a list"
                do_not: []
            """)
        with pytest.raises(CodesSchemaError, match="recommended_actions.*must be a list"):
            load_codes(path)

    def test_loader_rejects_for_llm_recommended_action_not_a_mapping(self, tmp_path):
        # An entry inside recommended_actions that isn't a dict.
        path = _write_yaml(tmp_path, """
            E_DEMO:
              severity: error
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
              for_llm:
                summary: short
                recommended_actions:
                  - "not a mapping"
                do_not: []
            """)
        with pytest.raises(CodesSchemaError, match="recommended_actions\\[0\\].*must be a"):
            load_codes(path)

    def test_loader_rejects_for_llm_do_not_item_not_a_string(self, tmp_path):
        path = _write_yaml(tmp_path, """
            E_DEMO:
              severity: error
              description: demo
              refs:
                state_path:
                  type: str
                  required: true
                  description: x
              for_llm:
                summary: short
                recommended_actions: []
                do_not:
                  - 42
            """)
        with pytest.raises(CodesSchemaError, match="do_not\\[0\\].*must be a string"):
            load_codes(path)
