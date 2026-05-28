"""
Unit tests for :mod:`pyfcstm.diagnostics.codes` — the loader that parses
``codes.yaml`` and exposes :data:`pyfcstm.diagnostics.codes.CODE_REGISTRY` as
the single source of truth for diagnostic codes.

These tests pin down the schema contract that downstream consumers
(``research_ideas`` LLM agent loop, future jsfcstm visualization, IDE
integrations) rely on, and verify the loader's structural validation
fails fast when the YAML is malformed.
"""

import os
import textwrap

import pytest

from pyfcstm.diagnostics import (
    CODE_REGISTRY,
    CodeFieldSpec,
    CodeSpec,
    CodesSchemaError,
    load_codes,
)
from pyfcstm.diagnostics.codes import _ALLOWED_REF_TYPES, _ALLOWED_SEVERITIES


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

    def test_rejects_missing_description_key(self, tmp_path):
        # Distinct from `description: ""` — this is the "key not present
        # at all" branch; both must hit the same raise.
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
        """)
        with pytest.raises(CodesSchemaError, match='description'):
            load_codes(path)

    def test_rejects_required_as_quoted_string(self, tmp_path):
        # YAML footgun: `required: "false"` is loaded as the string "false",
        # and `bool("false")` is True. Without strict bool check, required/
        # optional semantics would silently invert.
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Bad required.
              refs:
                bar:
                  type: str
                  required: "false"
                  description: A bar.
        """)
        with pytest.raises(CodesSchemaError, match='required'):
            load_codes(path)

    def test_rejects_refs_as_string(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Bad refs.
              refs: "not_a_mapping"
        """)
        with pytest.raises(CodesSchemaError, match='refs'):
            load_codes(path)

    def test_rejects_top_level_int_key(self, tmp_path):
        # YAML allows non-string keys at the top level; the loader must
        # reject them since code identifiers are strings by contract.
        target = tmp_path / 'codes.yaml'
        target.write_text(
            '123:\n'
            '  severity: error\n'
            '  description: bad.\n'
            '  refs:\n'
            '    x: {type: str, required: true, description: "x"}\n',
            encoding='utf-8',
        )
        with pytest.raises(CodesSchemaError, match='top-level key'):
            load_codes(str(target))

    def test_rejects_field_missing_type(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Missing type.
              refs:
                bar:
                  required: true
                  description: A bar.
        """)
        with pytest.raises(CodesSchemaError, match="'type'"):
            load_codes(path)

    def test_rejects_field_as_non_mapping(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Bad field shape.
              refs:
                bar: "not_a_mapping"
        """)
        with pytest.raises(CodesSchemaError, match='must be a mapping'):
            load_codes(path)

    def test_rejects_enum_as_non_list(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Bad enum shape.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
                  enum: "not_a_list"
        """)
        with pytest.raises(CodesSchemaError, match='enum'):
            load_codes(path)

    def test_rejects_enum_as_empty_list(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Empty enum.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
                  enum: []
        """)
        with pytest.raises(CodesSchemaError, match='non-empty'):
            load_codes(path)

    def test_rejects_enum_with_non_string_member(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Mixed enum.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
                  enum: ['ok', 42, 'still_ok']
        """)
        with pytest.raises(CodesSchemaError, match='strings'):
            load_codes(path)

    def test_accepts_field_without_enum(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: No-enum field is fine.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
        """)
        reg = load_codes(path)
        assert reg['E_FOO'].refs_schema['bar'].enum is None

    def test_loads_enum_into_code_field_spec(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: With enum.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
                  enum: ['a', 'b', 'c']
        """)
        reg = load_codes(path)
        spec = reg['E_FOO'].refs_schema['bar']
        assert spec.enum == ('a', 'b', 'c')

    def test_rejects_example_dsl_as_non_string(self, tmp_path):
        path = self._write_yaml(tmp_path, """
            E_FOO:
              severity: error
              description: Bad example_dsl.
              refs:
                bar:
                  type: str
                  required: true
                  description: A bar.
              example_dsl: [1, 2, 3]
        """)
        with pytest.raises(CodesSchemaError, match='example_dsl'):
            load_codes(path)

    def test_schema_errors_subclass_value_error(self):
        # Backwards-compat: generic ``except ValueError`` should still catch.
        try:
            raise CodesSchemaError("test")
        except ValueError as e:
            assert isinstance(e, CodesSchemaError)

    def test_rejects_code_entry_as_non_mapping(self, tmp_path):
        # codes.py:191 — a top-level code key whose value is a scalar.
        target = tmp_path / 'codes.yaml'
        target.write_text('E_FOO: just_a_string\n', encoding='utf-8')
        with pytest.raises(CodesSchemaError, match='must be a mapping'):
            load_codes(str(target))

    def test_rejects_file_with_only_comments(self, tmp_path):
        # codes.py:290 — file parses to None / empty, distinct from
        # 'top-level non-mapping' branch.
        target = tmp_path / 'codes.yaml'
        target.write_text('# only comments\n# nothing else\n', encoding='utf-8')
        with pytest.raises(CodesSchemaError, match='empty'):
            load_codes(str(target))

    def test_rejects_empty_mapping_at_root(self, tmp_path):
        # codes.py: the `if not registry:` branch — distinct from `is None`
        # (only comments) and from `non-mapping root` (a list at top level).
        target = tmp_path / 'codes.yaml'
        target.write_text('{}\n', encoding='utf-8')
        with pytest.raises(CodesSchemaError, match='no code definitions'):
            load_codes(str(target))

    def test_real_codes_yaml_path_resolves(self):
        path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'pyfcstm', 'diagnostics', 'codes.yaml',
        )
        assert os.path.isfile(path)
        reg = load_codes(path)
        assert set(reg.keys()) == set(CODE_REGISTRY.keys())


@pytest.mark.unittest
class TestRegistryImmutability:
    """The registry is exposed as MappingProxyType — verify it really is."""

    def test_registry_cannot_be_assigned_into(self):
        with pytest.raises(TypeError):
            CODE_REGISTRY['E_NEW_CODE'] = None  # type: ignore[index]

    def test_refs_schema_cannot_be_assigned_into(self):
        spec = CODE_REGISTRY['E_UNDEFINED_VAR']
        with pytest.raises(TypeError):
            spec.refs_schema['injected_field'] = None  # type: ignore[index]


@pytest.mark.unittest
class TestResolveCodesYamlPath:
    """
    I4 from PR-107 review: ``_resolve_codes_yaml_path`` must work both in
    normal install (``__file__`` next to ``codes.yaml``) and in PyInstaller
    one-file bundle (``sys._MEIPASS`` extraction root).
    """

    def test_resolves_under_normal_install(self):
        # The import-time CODE_REGISTRY proves the normal path works; this
        # test exists just to make the assertion explicit.
        from pyfcstm.diagnostics.codes import _resolve_codes_yaml_path
        path = _resolve_codes_yaml_path()
        assert os.path.isfile(path)
        assert path.endswith('codes.yaml')

    def test_resolves_under_meipass_bundle(self, tmp_path, monkeypatch):
        # Simulate the PyInstaller one-file bundle layout: codes.yaml lives
        # under <_MEIPASS>/pyfcstm/diagnostics/codes.yaml, NOT next to the
        # imported module's __file__. We do this by temporarily masking the
        # candidate path's existence and pointing _MEIPASS at a synthesized
        # bundle root that contains codes.yaml.
        import sys as _sys
        import pyfcstm.diagnostics.codes as codes_mod

        bundle_root = tmp_path / 'meipass'
        target_dir = bundle_root / 'pyfcstm' / 'diagnostics'
        target_dir.mkdir(parents=True)
        (target_dir / 'codes.yaml').write_text(
            'E_FOO:\n'
            '  severity: error\n'
            '  description: bundled.\n'
            '  refs:\n'
            '    x: {type: str, required: true, description: "x"}\n',
            encoding='utf-8',
        )

        # Force the candidate path (next to __file__) to look missing by
        # pointing __file__ at a non-existent directory.
        fake_pkg_dir = tmp_path / 'no_such_pkg'
        fake_pkg_dir.mkdir()
        fake_file = fake_pkg_dir / 'codes.py'
        monkeypatch.setattr(codes_mod, '__file__', str(fake_file))
        monkeypatch.setattr(_sys, '_MEIPASS', str(bundle_root), raising=False)

        resolved = codes_mod._resolve_codes_yaml_path()
        assert os.path.isfile(resolved)
        assert str(bundle_root) in resolved

    def test_last_ditch_returns_candidate_path(self, tmp_path, monkeypatch):
        # codes.py:321 — if neither candidate nor _MEIPASS resolves to a
        # real file, the function returns the candidate so a subsequent
        # FileNotFoundError points at the expected location.
        import sys as _sys
        import pyfcstm.diagnostics.codes as codes_mod

        fake_pkg_dir = tmp_path / 'no_such_pkg'
        fake_pkg_dir.mkdir()
        fake_file = fake_pkg_dir / 'codes.py'
        monkeypatch.setattr(codes_mod, '__file__', str(fake_file))
        monkeypatch.delattr(_sys, '_MEIPASS', raising=False)

        resolved = codes_mod._resolve_codes_yaml_path()
        # candidate path returned even though it doesn't exist
        assert resolved.endswith('codes.yaml')
        assert not os.path.isfile(resolved)


@pytest.mark.unittest
class TestYamlCommentBlockSync:
    """
    M6 from PR-107 review: the type-token comment block at the top of
    codes.yaml must mirror ``_ALLOWED_REF_TYPES`` (single source of truth
    in codes.py). Drift would silently let new tokens land in the comment
    but not in the loader, or vice versa.
    """

    def test_comment_block_lists_all_allowed_types(self):
        path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'pyfcstm', 'diagnostics', 'codes.yaml',
        )
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        # Comment block uses ` | `-separated list. Extract any tokens in
        # backticks doesn't apply here (raw text). We assert each allowed
        # type appears at least once in the comment area (before the first
        # top-level YAML key, which is `E_UNDEFINED_VAR:` per the schema).
        head = text.split('E_UNDEFINED_VAR:', 1)[0]
        for ref_type in _ALLOWED_REF_TYPES:
            assert ref_type in head, (
                f"type token {ref_type!r} listed in _ALLOWED_REF_TYPES but "
                f"not documented in the codes.yaml comment block"
            )

    def test_schema_check_type_predicates_cover_all_allowed_types(self):
        """M3 from PR #115 final review: ``_schema_check._TYPE_PREDICATES``
        is the runtime side of the contract — every token in
        ``_ALLOWED_REF_TYPES`` must have a matching predicate, otherwise
        the schema check silently falls through to "always pass" and a
        typo or new token slips by undetected.
        """
        from ._schema_check import _TYPE_PREDICATES
        missing = set(_ALLOWED_REF_TYPES) - set(_TYPE_PREDICATES.keys())
        assert not missing, (
            f"type tokens declared in _ALLOWED_REF_TYPES but missing a "
            f"predicate in _TYPE_PREDICATES: {sorted(missing)}. Add a "
            f"matching lambda to _schema_check._TYPE_PREDICATES so the "
            f"runtime schema check actually validates the new type."
        )
        # And vice versa: every predicate must correspond to an allowed
        # type — leftover predicates are dead code.
        extra = set(_TYPE_PREDICATES.keys()) - set(_ALLOWED_REF_TYPES)
        assert not extra, (
            f"_TYPE_PREDICATES has predicates for type tokens not in "
            f"_ALLOWED_REF_TYPES: {sorted(extra)}. Remove the dead "
            f"predicate(s) or add the token to _ALLOWED_REF_TYPES."
        )
