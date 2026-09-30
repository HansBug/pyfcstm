"""Static checks of history declarations, targets and reserved names."""

import re

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import load_state_machine_from_text, parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.utils.validate import ModelValidationError

from test.model.test_history_lowering import EVENTS, WASHER


def _collect(text):
    return parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(text, "state_machine_dsl"), collect=True
    )


def _only(diagnostics, code):
    found = [item for item in diagnostics if item.code == code]
    assert found, [item.code for item in diagnostics]
    return found


def _machine(inner="", outer="", extra=""):
    """Owner ``R.O`` with ``inner`` in its body and ``outer`` in the root."""
    return """
    def int x = 0;
    %s
    state R {
        state Off;
        state O {
            state A;
            state W { state W1; state W2; [*] -> W1; }
            pseudo state P;
            [*] -> A;
            %s
        }
        [*] -> Off;
        Off -> O :: Fresh;
        !O -> Off :: Stop;
        %s
    }
    """ % (extra, inner, outer)


@pytest.mark.unittest
class TestHistoryDeclarationErrors:
    @pytest.mark.parametrize(
        ["inner", "outer", "reason"],
        [
            ("[H] -> A; [H] -> A;", "Off -> O.[H] :: Resume;", "duplicate"),
            ("[H] -> W.W1;", "Off -> O.[H] :: Resume;", "default_not_direct_child"),
            ("[H*] -> W.Nope;", "Off -> O.[H*] :: Resume;", "default_not_found"),
            ("[H*] -> A.Deeper;", "Off -> O.[H*] :: Resume;", "default_not_found"),
            ("[H] -> Nope;", "Off -> O.[H] :: Resume;", "default_not_found"),
            ("[H*] -> P;", "Off -> O.[H*] :: Resume;", "default_pseudo"),
        ],
    )
    def test_invalid_declarations_are_reported(self, inner, outer, reason):
        text = _machine(inner, outer)
        machine, diagnostics = _collect(text)
        (item,) = _only(diagnostics, "E_HISTORY_DECLARATION_INVALID")
        assert item.severity == "error"
        assert item.refs["reason"] == reason
        assert item.refs["owner_path"] == "R.O"
        assert item.span is not None
        with pytest.raises(ModelValidationError):
            load_state_machine_from_text(text)

    def test_the_root_state_cannot_own_history(self):
        text = "state R { state A; [*] -> A; [H] -> A; }"
        _, diagnostics = _collect(text)
        (item,) = _only(diagnostics, "E_HISTORY_DECLARATION_INVALID")
        assert item.refs["reason"] == "root_owner"
        assert item.refs["owner_path"] == "R"


@pytest.mark.unittest
class TestHistoryTargetErrors:
    @pytest.mark.parametrize(
        ["text", "owner", "kind"],
        [
            (
                "state R { state A; state O { state B; [*] -> B; } [*] -> A; A -> O.[H]; }",
                "R.O",
                "shallow",
            ),
            (
                "state R { state A; state O { state B; [*] -> B; [H] -> B; } [*] -> A; A -> O.[H*]; }",
                "R.O",
                "deep",
            ),
            (
                "state R { state A; state L; [*] -> A; A -> L.[H]; }",
                "R.L",
                "shallow",
            ),
            (
                "state R { state A; state O { state B; [*] -> B; } [*] -> A; !A -> O.[H*] :: Go; }",
                "R.O",
                "deep",
            ),
        ],
    )
    def test_targets_need_a_matching_declaration(self, text, owner, kind):
        _, diagnostics = _collect(text)
        (item,) = _only(diagnostics, "E_HISTORY_TARGET_UNDECLARED")
        assert item.refs == {"owner_path": owner, "kind": kind}
        assert item.span is not None

    def test_unknown_target_state_keeps_the_existing_diagnostic(self):
        _, diagnostics = _collect("state R { state A; [*] -> A; A -> Nope.[H]; }")
        codes = {item.code for item in diagnostics}
        assert "E_HISTORY_TARGET_UNDECLARED" not in codes
        assert any(item.severity == "error" for item in diagnostics)


@pytest.mark.unittest
class TestHistoryUnused:
    def test_declared_but_unreferenced_history_warns_and_adds_nothing(self):
        text = "state R { state A; state O { state B; [*] -> B; [H] -> B; [H*] -> B; } [*] -> A; A -> O :: Go; }"
        machine, diagnostics = _collect(text)
        items = _only(diagnostics, "W_HISTORY_UNUSED")
        assert sorted(item.refs["kind"] for item in items) == ["deep", "shallow"]
        assert all(item.severity == "warning" and item.refs["owner_path"] == "R.O" for item in items)
        assert machine.history_owners == ()
        assert not any(name.startswith("__hist_") for name in machine.defines)

    def test_an_unreferenced_kind_does_not_add_routes(self):
        text = """
        state R {
            state Off;
            state O {
                state A;
                state W { state W1; state W2; [*] -> W1; W1 -> W2 :: Go; }
                [*] -> A;
                [H] -> A;
                [H*] -> W.W1;
            }
            [*] -> Off;
            Off -> O.[H] :: Resume;
            !O -> Off :: Stop;
        }
        """
        machine, diagnostics = _collect(text)
        (item,) = _only(diagnostics, "W_HISTORY_UNUSED")
        assert item.refs["kind"] == "deep"
        (owner,) = machine.history_owners
        assert owner.defaults == {"shallow": ("A",), "deep": ("W", "W1")}
        w = machine.root_state.substates["O"].substates["W"]
        # Only shallow history is used, so no route goes below W.
        assert len(w.init_transitions) == 1


@pytest.mark.unittest
class TestReservedHistoryNames:
    @pytest.mark.parametrize(
        ["extra", "body", "identifier", "kind"],
        [
            ("def int __hist_x = 0;", "", "__hist_x", "variable"),
            ("def int _hist_goto = 0;", "", "_hist_goto", "variable"),
            ("", "state __hist_gate_1;", "__hist_gate_1", "state"),
            ("", "A -> A :: Tick effect { __hist_tmp = 1; x = __hist_tmp; }", "__hist_tmp", "temporary"),
        ],
    )
    def test_reserved_names_are_errors_when_the_model_uses_history(self, extra, body, identifier, kind):
        text = _machine("[H] -> A; " + body, "Off -> O.[H] :: Resume;", extra=extra)
        _, diagnostics = _collect(text)
        items = [item for item in _only(diagnostics, "E_HISTORY_RESERVED_PREFIX") if item.refs["identifier"] == identifier]
        assert len(items) == 1
        assert items[0].refs["identifier_kind"] == kind

    def test_reserved_prefix_only_warns_without_history(self):
        text = "def int __hist_goto = 0; state R { state A; [*] -> A; }"
        machine, diagnostics = _collect(text)
        (item,) = _only(diagnostics, "W_HISTORY_RESERVED_PREFIX")
        assert item.severity == "warning"
        assert item.refs == {"identifier": "__hist_goto", "identifier_kind": "variable"}
        assert "__hist_goto" in machine.defines

    def test_single_underscore_names_are_fine_without_history(self):
        _, diagnostics = _collect("def int _hist_goto = 0; state R { state A; [*] -> A; }")
        assert diagnostics == []


@pytest.mark.unittest
class TestHistoryExport:
    def test_exported_text_is_plain_fcstm_with_the_same_behaviour(self):
        machine = load_state_machine_from_text(WASHER)
        exported = str(machine.to_ast_node())
        assert "[H" not in exported
        assert "__hist_goto" in exported
        reparsed, diagnostics = _collect(exported)
        assert {item.code for item in diagnostics} == {"W_HISTORY_RESERVED_PREFIX"}
        assert reparsed.history_owners == ()

        script = [None, "Fresh", "Start", "Filled", "Pause", "Deep", "Pause", "Shallow"]
        states = []
        for model in (machine, reparsed):
            runtime = SimulationRuntime(model)
            trace = []
            for event in script:
                runtime.cycle([EVENTS[event]] if event else [])
                trace.append((".".join(runtime.current_state.path), dict(runtime.vars)))
            states.append(trace)
        assert states[0] == states[1]

    def test_exported_evented_gate_round_trips(self):
        text = """
        state R {
            state Off;
            state O {
                event Kick;
                state A;
                [*] -> A :: Kick;
                [H] -> A;
            }
            [*] -> Off;
            Off -> O.[H] :: Resume;
            !O -> Off :: Stop;
        }
        """
        machine = load_state_machine_from_text(text)
        exported = str(machine.to_ast_node())
        reparsed, diagnostics = _collect(exported)
        assert all(item.severity == "warning" for item in diagnostics)
        assert str(reparsed.to_ast_node()) == exported


@pytest.mark.unittest
@pytest.mark.parametrize(
    "text",
    [
        _machine("[H] -> W.W1;", "Off -> O.[H] :: Resume;"),
        "state R { state A; [*] -> A; [H] -> A; }",
        "state R { state A; state O { state B; [*] -> B; } [*] -> A; A -> O.[H]; }",
        _machine("[H] -> A;", "Off -> O.[H] :: Resume;", extra="def int __hist_x = 0;"),
        "def int __hist_goto = 0; state R { state A; [*] -> A; }",
        "state R { state A; state O { state B; [*] -> B; [H] -> B; } [*] -> A; A -> O :: Go; }",
    ],
)
def test_history_diagnostics_match_the_code_registry(text):
    from pyfcstm.diagnostics import CODE_REGISTRY

    _, diagnostics = _collect(text)
    history = [item for item in diagnostics if "HISTORY" in item.code]
    assert history
    for item in history:
        spec = CODE_REGISTRY.get(item.code)
        assert spec is not None
        assert spec.severity == item.severity
        assert set(item.refs) <= set(spec.refs_schema)
        assert set(spec.required_fields()) <= set(item.refs)
        for name, value in item.refs.items():
            allowed = spec.refs_schema[name].enum
            assert not allowed or value in allowed


@pytest.mark.unittest
@pytest.mark.parametrize("mode", ["legend", "note"])
def test_plantuml_keeps_lowered_history_names_literal(mode):
    from pyfcstm.model import PlantUMLOptions

    machine = load_state_machine_from_text(WASHER)
    source = machine.to_plantuml(
        PlantUMLOptions(detail_level="full", variable_display_mode=mode)
    )
    # Creole treats ``__`` as underline markup, so notes, legends and state
    # descriptions escape every lowered name; link labels are not Creole.
    creole = []
    for line in source.splitlines():
        if "__hist_" not in line or "-->" in line:
            continue
        # A state description is ``alias : text``; the alias is an identifier.
        head, sep, tail = line.partition(" : ")
        if sep and re.fullmatch(r"\s*\w+", head):
            line = tail
        creole.append(line)
    assert creole
    assert all("__" not in line.replace("~__", "") for line in creole), creole
    assert any("~__hist_goto = (~__hist_Program" in line for line in creole)
    plain = load_state_machine_from_text("def int a = 0; state R { state A; [*] -> A; }")
    assert "~" not in plain.to_plantuml(PlantUMLOptions(detail_level="full", variable_display_mode=mode))
