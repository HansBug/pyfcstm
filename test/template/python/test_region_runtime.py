"""Generated Python runtime for models that declare regions: public surface, hooks and guides."""

import re
import sys
from pathlib import Path

import pytest

from test.template.readme_examples import example_code
from test.template.python.test_runtime import (
    _python_code_blocks,
    _render_python_artifacts,
    _render_python_module,
)

pytestmark = pytest.mark.unittest

OWNER_MODEL = """
def int n = 0;
state Root {
    [*] -> Run;
    state Run {
        exit abstract Left;
        region A {
            [*] -> X;
            state X { during { n = n + 1; } event Stop; }
            X -> [*] :: Stop;
        }
        region B {
            [*] -> Y;
            state Y;
        }
    }
}
"""


def test_position_is_one_line_of_text_with_queries_about_it():
    with _render_python_module(OWNER_MODEL) as module:
        machine = module.RootMachine()
        machine.cycle()
        assert machine.configuration == "Root.Run{A: X, B: Y}"
        assert machine.vars == {"n": 1}
        assert machine.region_status("Root.Run.A") == "live"
        assert machine.is_active("Root.Run.A.X")
        assert machine.leaves == (("Root", "Run", "A", "X"), ("Root", "Run", "B", "Y"))

        machine.cycle(["Stop"])
        assert machine.configuration == "Root.Run{A: [done], B: Y}"
        assert machine.region_status("Root.Run.A") == "done"
        assert machine.region_status("Root.Run.B") == "live"
        assert not machine.is_active("Root.Run.A.X")
        assert machine.leaves == (("Root", "Run", "B", "Y"),)
        assert machine.vars == {"n": 1}


def test_region_status_names_the_owner_that_is_not_in_the_position():
    source = """
    state Root {
        [*] -> Idle;
        state Idle;
        state Run {
            region A { [*] -> X; state X; }
        }
        Idle -> Run :: Go;
    }
    """
    with _render_python_module(source) as module:
        machine = module.RootMachine()
        machine.cycle()
        assert machine.region_status("Root.Run.A") == "inactive"
        machine.cycle(["Go"])
        assert machine.region_status("Root.Run.A") == "live"
        with pytest.raises(ValueError):
            machine.region_status("Root.Run")
        with pytest.raises(ValueError):
            machine.region_status("Root.Nowhere")


def test_a_machine_with_regions_has_no_single_path_position():
    with _render_python_module(OWNER_MODEL) as module:
        machine = module.RootMachine()
        machine.cycle()
        for name in ("current_state_path", "current_state_name"):
            assert not hasattr(machine, name)
            with pytest.raises(AttributeError):
                getattr(machine, name)
        assert machine.info()["configuration"] == "Root.Run{A: X, B: Y}"
        assert "current_state_path" not in machine.info()


def test_a_machine_without_regions_keeps_its_single_path_position():
    source = "state Root { [*] -> Idle; state Idle; }"
    with _render_python_module(source) as module:
        machine = module.RootMachine()
        machine.cycle()
        assert machine.current_state_path == ("Root", "Idle")
        assert machine.current_state_name == "Idle"
        assert machine.info()["current_state_path"] == ("Root", "Idle")


def test_state_can_only_be_read_from_outside():
    with _render_python_module(OWNER_MODEL) as module:
        machine = module.RootMachine()
        machine.cycle()
        view = machine.vars
        with pytest.raises(TypeError):
            view["n"] = 99
        assert view["n"] == 1
        machine.cycle()
        assert machine.vars["n"] == 2
        assert dict(machine.vars) == {"n": 2}
        assert not hasattr(machine, "variables")
        with pytest.raises(TypeError):
            module.RootMachine.ABSTRACT_HOOKS["Root.Run.Left"] = "x"


@pytest.mark.parametrize(
    "initial_state, shown, after_first_cycle, n",
    [
        ("Root.Run{B: Y}", "Root.Run{A: [init], B: Y}", "Root.Run{A: X, B: Y}", 6),
        ("Root.Run", "Root.Run{A: [init], B: [init]}", "Root.Run{A: X, B: Y}", 6),
        ("Root.Run.B.Y", "Root.Run{A: [init], B: Y}", "Root.Run{A: X, B: Y}", 6),
        ("Root.Run{A: [done], B: Y}", "Root.Run{A: [done], B: Y}", "Root.Run{A: [done], B: Y}", 5),
    ],
)
def test_hot_start_puts_what_is_written_in_place_and_initializes_the_rest(
    initial_state, shown, after_first_cycle, n
):
    with _render_python_module(OWNER_MODEL) as module:
        machine = module.RootMachine(initial_state=initial_state, initial_vars={"n": 5})
        assert machine.configuration == shown
        machine.cycle()
        assert machine.configuration == after_first_cycle
        assert machine.vars == {"n": n}


def test_a_region_that_waits_for_initialization_is_pending_until_the_first_cycle():
    with _render_python_module(OWNER_MODEL) as module:
        machine = module.RootMachine(initial_state="Root.Run{B: Y}", initial_vars={"n": 5})
        assert machine.region_status("Root.Run.A") == "pending"
        assert machine.region_status("Root.Run.B") == "live"
        assert machine.leaves == (("Root", "Run", "B", "Y"),)
        machine.cycle()
        assert machine.region_status("Root.Run.A") == "live"


def test_hot_start_refuses_an_owner_whose_regions_are_all_done():
    with _render_python_module(OWNER_MODEL) as module:
        with pytest.raises(ValueError, match="All regions are Done at 'Root.Run'"):
            module.RootMachine(
                initial_state="Root.Run{A: [done], B: [done]}", initial_vars={"n": 0}
            )


def test_hooks_of_an_owner_see_the_position_at_the_moment_of_the_call():
    calls = []
    source = OWNER_MODEL.replace("[*] -> Run;", "[*] -> Run;\n    !Run -> [*] :: Quit;")
    with _render_python_module(source) as module:

        class Machine(module.RootMachine):
            def _abstract_hook_Root_Run_Left(self, ctx):
                calls.append((ctx.state_path, ctx.active_leaf, ctx.configuration))

        machine = Machine()
        machine.cycle()
        assert calls == []
        machine.cycle(["Root.Run.Quit"])
        assert machine.is_ended
        # While the owner is left, the regions that have left already show as done.
        assert calls == [
            (("Root", "Run"), ("Root", "Run"), "Root.Run{A: [done], B: [done]}")
        ]


def test_names_that_differ_only_in_case_keep_their_own_hooks():
    source = """
    def int hits = 0;
    state Root {
        [*] -> Run;
        state Run {
            region Alpha {
                [*] -> Work;
                state Work { enter abstract Init; }
            }
            region alpha {
                [*] -> Work;
                state Work { enter abstract Init; }
            }
        }
    }
    """
    calls = []
    with _render_python_module(source) as module:
        hooks = module.RootMachine.get_abstract_hook_map()
        assert sorted(hooks) == ["Root.Run.Alpha.Work.Init", "Root.Run.alpha.Work.Init"]
        assert len(set(hooks.values())) == 2

        class Machine(module.RootMachine):
            def _abstract_hook_Root_Run_Alpha_Work_Init(self, ctx):
                calls.append("Alpha")

            def _abstract_hook_Root_Run_alpha_Work_Init(self, ctx):
                calls.append("alpha")

        machine = Machine()
        machine.cycle()
        assert machine.configuration == "Root.Run{Alpha: Work, alpha: Work}"
        assert calls == ["Alpha", "alpha"]


@pytest.mark.parametrize("language", ["en", "zh"])
def test_guide_examples_run_for_a_model_with_regions(language, monkeypatch):
    with _render_python_artifacts(OWNER_MODEL) as artifacts:
        monkeypatch.setitem(sys.modules, "machine", artifacts["module"])
        key = "readme_file" if language == "en" else "readme_zh_file"
        markdown = Path(artifacts[key]).read_text(encoding="utf-8")
        namespace = {}
        exec(example_code(markdown, "quick-start"), namespace)
        machine = namespace["machine"]
        assert machine.configuration == "Root.Run{A: X, B: Y}"
        exec(example_code(markdown, "regions"), namespace)
        assert namespace["machine"].leaves == (
            ("Root", "Run", "A", "X"),
            ("Root", "Run", "B", "Y"),
        )
        exec(example_code(markdown, "hot-start"), namespace)
        restored = namespace["machine"]
        assert restored is not machine
        assert restored.configuration == "Root.Run{A: X, B: Y}"
        assert restored.vars == machine.vars
        assert "current_state_path" not in "\n".join(_python_code_blocks(markdown))
        assert "AttributeError" in markdown
        assert "[init]" in markdown and "[done]" in markdown


def test_guides_of_a_region_model_are_structurally_equivalent():
    with _render_python_artifacts(OWNER_MODEL) as artifacts:
        english = Path(artifacts["readme_file"]).read_text(encoding="utf-8")
        chinese = Path(artifacts["readme_zh_file"]).read_text(encoding="utf-8")
    for pattern in (r"^#{1,3} ", r"<!-- example:[a-z-]+ -->", r"^```", r'<a id="[a-z]+"></a>'):
        assert len(re.findall(pattern, english, re.M)) == len(
            re.findall(pattern, chinese, re.M)
        ), pattern
    assert "Region paths" in english and "Region 路径" in chinese
    # Prose paragraphs stay on one physical line in the rendered guides.
    for text in (english, chinese):
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        for paragraph in prose.split("\n\n"):
            paragraph = paragraph.strip()
            if paragraph and paragraph[0] not in "|-*<#{":
                assert "\n" not in paragraph, paragraph[:80]
