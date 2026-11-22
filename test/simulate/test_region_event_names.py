"""Public-surface tests for external event names in a model with regions.

A full path and a name that starts at the root (``/Name``) mean the same
wherever the machine rests. A name that depends on the position (a short name,
or one that counts levels up with leading dots) is resolved once for every
active leaf: no leaf finds an event, it is an error; the leaves that find one
all find the same event, it is used; they find different events, the name is
ambiguous and the candidates are listed. Events with the same name that belong
to different states are different events and are never broadcast.
"""

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.model.configuration import Configuration
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeEventError
from pyfcstm.utils.validate import ModelLookupError, ModelValueError

pytestmark = pytest.mark.unittest

MODEL = """
def int trail = 0;
state Controller {
    event Reset;
    [*] -> Idle;
    state Idle;
    Idle -> Running :: Start;
    state Running {
        event Stop;
        region Safety {
            [*] -> Watching;
            state Watching { event Trip; event Ping; }
            state Tripped;
            Watching -> Tripped :: Trip;
            Watching -> [*] : /Reset;
            Watching -> Watching :: Ping effect { trail = trail * 10 + 1; }
        }
        region Motion {
            [*] -> Off;
            state Off { event Go; event Ping; }
            state On;
            Off -> On :: Go;
            Off -> Off :: Ping effect { trail = trail * 10 + 2; }
        }
    }
}
"""

RESTING = "Controller.Running{Safety: Watching, Motion: Off}"


@pytest.fixture(scope="module")
def model():
    return load_state_machine_from_text(MODEL)


def _running(model):
    runtime = SimulationRuntime(model)
    runtime.cycle()
    runtime.cycle(["Controller.Idle.Start"])
    assert str(runtime.configuration) == RESTING
    return runtime


@pytest.mark.parametrize(
    ["name", "expected"],
    [
        pytest.param("Trip", "Controller.Running.Safety.Watching.Trip", id="only-one-leaf-has-it"),
        pytest.param("Go", "Controller.Running.Motion.Off.Go", id="only-the-other-leaf-has-it"),
        pytest.param("..Stop", "Controller.Running.Stop", id="every-leaf-counts-up-to-one-event"),
        pytest.param("/Reset", "Controller.Reset", id="from-the-root"),
    ],
)
def test_a_name_that_leads_to_one_event_is_used(model, name, expected):
    config = Configuration.parse(model, RESTING)
    assert config.resolve_event(name).path_name == expected


def test_a_name_that_leads_to_different_events_is_ambiguous(model):
    config = Configuration.parse(model, RESTING)
    with pytest.raises(ModelValueError) as caught:
        config.resolve_event("Ping")
    message = str(caught.value)
    assert "ambiguous" in message
    assert "Controller.Running.Safety.Watching.Ping" in message
    assert "Controller.Running.Motion.Off.Ping" in message


def test_a_name_that_no_leaf_finds_is_an_error(model):
    config = Configuration.parse(model, RESTING)
    with pytest.raises(ModelLookupError, match="Nope"):
        config.resolve_event("Nope")
    with pytest.raises(ModelLookupError, match="Nope"):
        config.resolve_event("..Nope")


def test_a_name_that_reaches_above_the_root_from_every_leaf_is_an_error(model):
    config = Configuration.parse(model, RESTING)
    with pytest.raises(ValueError):
        config.resolve_event("........Stop")


def test_the_leaves_of_a_finished_region_do_not_take_part(model):
    config = Configuration.parse(model, "Controller.Running{Safety: [done], Motion: Off}")
    assert config.resolve_event("Ping").path_name == "Controller.Running.Motion.Off.Ping"


def test_a_single_leaf_resolves_as_before(model):
    config = Configuration.parse(model, "Controller.Idle")
    assert config.resolve_event("Start").path_name == "Controller.Idle.Start"
    assert config.resolve_event(".Reset").path_name == "Controller.Reset"


def test_the_runtime_uses_the_name_of_the_leaf_that_has_it(model):
    runtime = _running(model)
    runtime.cycle(["Go"])
    assert str(runtime.configuration) == "Controller.Running{Safety: Watching, Motion: On}"


def test_the_runtime_reports_an_ambiguous_name_with_its_candidates(model):
    runtime = _running(model)
    with pytest.raises(SimulationRuntimeEventError, match="ambiguous") as caught:
        runtime.cycle(["Ping"])
    assert "Controller.Running.Motion.Off.Ping" in str(caught.value)
    # Nothing ran: the cycle was refused before it started.
    assert runtime.vars["trail"] == 0
    assert runtime.cycle_count == 2


def test_the_runtime_reports_a_name_nobody_has(model):
    runtime = _running(model)
    with pytest.raises(SimulationRuntimeEventError, match="Nope"):
        runtime.cycle(["Nope"])


def test_the_runtime_accepts_the_full_path_of_the_ambiguous_name(model):
    runtime = _running(model)
    runtime.cycle(["Controller.Running.Motion.Off.Ping"])
    assert runtime.vars["trail"] == 2
    runtime.cycle(["Controller.Running.Safety.Watching.Ping"])
    assert runtime.vars["trail"] == 21


def test_two_names_in_one_cycle_are_resolved_on_their_own(model):
    runtime = _running(model)
    runtime.cycle(["Trip", "Go"])
    assert str(runtime.configuration) == "Controller.Running{Safety: Tripped, Motion: On}"


def test_the_name_depends_on_where_the_hot_start_put_the_machine(model):
    runtime = SimulationRuntime(
        model,
        initial_state="Controller.Running{Safety: Watching, Motion: On}",
        initial_vars={"trail": 0},
    )
    with pytest.raises(SimulationRuntimeEventError, match="Go"):
        runtime.cycle(["Go"])
    runtime.cycle(["Ping"])
    assert runtime.vars["trail"] == 1


UNEVEN = """
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        region Shallow { [*] -> X; state X; X -> X : /Stop; }
        region Deep {
            [*] -> Mid;
            state Mid { [*] -> Y; state Y; }
        }
    }
}
"""


def test_a_name_that_is_malformed_from_one_leaf_is_still_found_from_another():
    """Four dots go above the root from the shallow leaf but reach ``Root.Stop`` from the deep one."""
    model = load_state_machine_from_text(UNEVEN)
    config = Configuration.parse(model, "Root.Run{Shallow: X, Deep: Mid.Y}")
    assert config.resolve_event("....Stop").path_name == "Root.Stop"
    # Seen from the shallow leaf alone it is malformed.
    shallow = Configuration.parse(model, "Root.Run{Shallow: X, Deep: [done]}")
    with pytest.raises(ModelValueError):
        shallow.resolve_event("....Stop")
