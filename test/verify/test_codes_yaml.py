"""
Unit tests for :mod:`pyfcstm.verify.codes` — the loader that parses
``codes.yaml`` and exposes :data:`pyfcstm.verify.codes.CODE_REGISTRY` as
the single source of truth for diagnostic codes.

These tests pin down the schema contract that downstream consumers
(``research_ideas`` LLM agent loop, future jsfcstm visualization, IDE
integrations) rely on, and verify the loader's structural validation
fails fast when the YAML is malformed.
"""

import os
import textwrap

import pytest

from pyfcstm.verify import CODE_REGISTRY, CodeFieldSpec, CodeSpec, load_codes
from pyfcstm.verify.codes import _ALLOWED_REF_TYPES, _ALLOWED_SEVERITIES


@pytest.mark.unittest
class TestCodeRegistryShape:
    def test_registry_is_non_empty(self):
        assert len(CODE_REGISTRY) >= 10, (
            "PR-1 introduces 10 error codes; the registry should never shrink "
            "below that floor without explicit removal in a follow-up PR."
        )

    def test_all_entries_are_code_specs(self):
        for code, spec in CODE_REGISTRY.items():
            assert isinstance(spec, CodeSpec)
            assert spec.code == code

    @pytest.mark.parametrize('code', sorted(CODE_REGISTRY.keys()))
    def test_each_code_has_valid_severity(self, code):
        assert CODE_REGISTRY[code].severity in _ALLOWED_SEVERITIES

    @pytest.mark.parametrize('code', sorted(CODE_REGISTRY.keys()))
    def test_each_code_has_non_empty_description(self, code):
        assert CODE_REGISTRY[code].description.strip()

    @pytest.mark.parametrize('code', sorted(CODE_REGISTRY.keys()))
    def test_each_code_has_at_least_one_ref_field(self, code):
        assert len(CODE_REGISTRY[code].refs_schema) >= 1, (
            f"code {code} has no refs schema; a diagnostic without any "
            f"structured payload is rarely useful to downstream tooling."
        )

    @pytest.mark.parametrize('code', sorted(CODE_REGISTRY.keys()))
    def test_each_ref_field_uses_allowed_type(self, code):
        for field_name, field_spec in CODE_REGISTRY[code].refs_schema.items():
            assert isinstance(field_spec, CodeFieldSpec)
            assert field_spec.type in _ALLOWED_REF_TYPES, (
                f"code {code} field {field_name} uses unsupported type "
                f"{field_spec.type!r}"
            )

    def test_error_codes_use_E_prefix(self):
        for code, spec in CODE_REGISTRY.items():
            if spec.severity == 'error':
                assert code.startswith('E_'), (
                    f"error code {code} must start with 'E_'"
                )

    def test_warning_codes_use_W_prefix(self):
        for code, spec in CODE_REGISTRY.items():
            if spec.severity == 'warning':
                assert code.startswith('W_'), (
                    f"warning code {code} must start with 'W_'"
                )


@pytest.mark.unittest
class TestPR1CodesPresence:
    """
    Lock in the exact set of error codes introduced by PR-1 so that future
    refactors removing or renaming any of them surface as an obvious test
    failure (downstream contract guard).
    """

    PR1_CODES = {
        'E_UNDEFINED_VAR',
        'E_DUPLICATE_VAR',
        'E_MISSING_STATE',
        'E_DUPLICATE_STATE',
        'E_EVENT_REF_INVALID',
        'E_EVENT_NOT_FOUND',
        'E_DANGLING_TRANSITION',
        'E_TYPE_MISMATCH',
        'E_FORCED_TRANSITION_EXPANSION',
        'E_INITIAL_TRANSITION_INVALID',
    }

    def test_all_pr1_codes_present(self):
        missing = self.PR1_CODES - set(CODE_REGISTRY)
        assert not missing, f"PR-1 codes missing from registry: {missing}"

    def test_e_undefined_var_required_fields(self):
        spec = CODE_REGISTRY['E_UNDEFINED_VAR']
        required = set(spec.required_fields())
        assert 'var_name' in required
        assert 'referenced_in' in required

    def test_e_missing_state_required_fields(self):
        spec = CODE_REGISTRY['E_MISSING_STATE']
        assert 'state_path' in spec.required_fields()

    def test_e_dangling_transition_reason_required(self):
        spec = CODE_REGISTRY['E_DANGLING_TRANSITION']
        assert 'reason' in spec.required_fields()


@pytest.mark.unittest
class TestLoaderValidation:
    def _write_yaml(self, tmp_path, body: str) -> str:
        target = tmp_path / 'codes.yaml'
        target.write_text(textwrap.dedent(body), encoding='utf-8')
        return str(target)

    def test_loads_minimal_valid_file(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: A test code.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
        """)
        reg = load_codes(path)
        assert 'E_FOO' in reg
        assert reg['E_FOO'].refs_schema['bar'].type == 'str'

    def test_rejects_unknown_severity(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: critical
              description: Bad severity.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
        """)
        with pytest.raises(ValueError, match='severity'):
            load_codes(path)

    def test_rejects_unknown_ref_type(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Bad ref type.
              refs:
                bar:
                  type: complex_thing
                  required: true
                  description: A bar.
        """)
        with pytest.raises(ValueError, match='unsupported type'):
            load_codes(path)

    def test_rejects_missing_description(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: ""
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
        """)
        with pytest.raises(ValueError, match='description'):
            load_codes(path)

    def test_rejects_severity_prefix_mismatch(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            W_FOO:
              severity: error
              description: Prefix and severity disagree.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
        """)
        with pytest.raises(ValueError, match='prefix'):
            load_codes(path)

    def test_rejects_empty_file(self, tmp_path):
        target = tmp_path / 'codes.yaml'
        target.write_text('', encoding='utf-8')
        with pytest.raises(ValueError, match='empty'):
            load_codes(str(target))

    def test_rejects_non_mapping_root(self, tmp_path):
        target = tmp_path / 'codes.yaml'
        target.write_text('- E_FOO\n', encoding='utf-8')
        with pytest.raises(ValueError, match='top-level mapping'):
            load_codes(str(target))

    def test_real_codes_yaml_path_resolves(self):
        path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'pyfcstm', 'verify', 'codes.yaml',
        )
        assert os.path.isfile(path)
        reg = load_codes(path)
        assert set(reg.keys()) == set(CODE_REGISTRY.keys())
