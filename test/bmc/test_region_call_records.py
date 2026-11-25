"""Abstract calls of a model with regions, decoded from a solved BMC trace.

Every model is run twice, in the simulator with a handler on each abstract
action and in the BMC relation pinned to the same events, and the two lists of
calls must agree call by call: the action, the state and active leaf the
handler reports, the stage, the variables it saw and the configuration of the
whole machine at the moment of the call.
"""

import pytest
import z3

from pyfcstm.bmc import BmcEngine, BmcError, build_bmc_core_formula
from pyfcstm.bmc.region_witness import trace_region_step
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest


def simulated_calls(text, actions, cycles):
    """Run the cycles in the simulator and return the calls of every cycle."""
    runtime = SimulationRuntime(load_state_machine_from_text(text))
    seen = []

    def record(ctx):
        seen.append(
            {
                "action": ctx.abstract_target or ctx.action_name,
                "state": ctx.get_full_state_path(),
                "stage": ctx.call_stage or ctx.action_stage,
                "active_leaf": ".".join(ctx.active_leaf or ctx.state_path),
                "named_ref": ctx.named_ref,
                "vars": dict(ctx.vars),
                "configuration": str(ctx.configuration),
            }
        )

    for action in actions:
        runtime.register_abstract_handler(action, record)
    per_cycle = []
    for events in cycles:
        seen.clear()
        runtime.cycle(list(events))
        per_cycle.append(list(seen))
    return per_cycle


def decoded_calls(text, cycles):
    """Pin the cycles in the BMC relation and decode the calls of every cycle."""
    model = load_state_machine_from_text(text)
    core = build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= %d: terminated();" % len(cycles))
    )
    pins = []
    for index, events in enumerate(cycles):
        for event in core.context.domain.events:
            literal = core.symbols.event_input(index, event.path)
            pins.append(literal if event.path in events else z3.Not(literal))
    solver = z3.Solver()
    solver.add(core.core, *pins)
    assert solver.check() == z3.sat
    solved = solver.model()
    return [
        [
            {
                "action": call.action_name,
                "state": call.state,
                "stage": call.stage,
                "active_leaf": call.active_leaf,
                "named_ref": call.named_ref,
                "vars": dict(call.snapshot),
                "configuration": call.configuration,
            }
            for call in trace_region_step(core, solved, index).calls
        ]
        for index in range(len(cycles))
    ]


WRAPPED_SCOPES = (
    """
    state Controller {
        event Start;
        >> during before abstract Tick;
        [*] -> Idle;
        state Idle;
        state Running {
            >> during before abstract GroupPre;
            region Safety {
                >> during before abstract SafetyPre;
                [*] -> Normal;
                state Normal { during abstract Watch; }
            }
            region Motion {
                [*] -> Off;
                state Off;
                state On { during abstract Drive; }
                Off -> On;
            }
        }
        Idle -> Running : /Start;
    }
    """,
    [
        "Controller.Tick",
        "Controller.Running.GroupPre",
        "Controller.Running.Safety.SafetyPre",
        "Controller.Running.Safety.Normal.Watch",
        "Controller.Running.Motion.On.Drive",
    ],
    [[], ["Controller.Start"], [], []],
)

AFTER_ASPECTS = (
    """
    def int n = 0;
    state Root {
        >> during after abstract RootDone;
        region A {
            >> during after abstract ADone;
            [*] -> P;
            state P { during { n = n + 1; } during abstract PWork; }
        }
        region B {
            [*] -> Q;
            state Q { during { n = n + 10; } during abstract QWork; }
        }
    }
    """,
    ["Root.RootDone", "Root.A.ADone", "Root.A.P.PWork", "Root.B.Q.QWork"],
    [[], [], []],
)

NESTED_GROUP = (
    """
    def int n = 0;
    state Root {
        event Go;
        [*] -> Outer;
        state Outer {
            region R1 {
                [*] -> Inner;
                state Inner {
                    enter abstract InnerIn;
                    region X { [*] -> X1; state X1 { during abstract XWork; } }
                    region Y { [*] -> Y1; state Y1 { during { n = n + 1; } } }
                }
            }
            region R2 { [*] -> S; state S { during abstract SWork; } }
        }
    }
    """,
    ["Root.Outer.R1.Inner.InnerIn", "Root.Outer.R1.Inner.X.X1.XWork", "Root.Outer.R2.S.SWork"],
    [[], [], []],
)

FORCED_EXIT = (
    """
    state Root {
        event Stop;
        [*] -> P;
        state P {
            enter abstract POn;
            exit abstract POff;
            region R1 { [*] -> A; state A { enter abstract AOn; exit abstract AOff; } }
            region R2 { [*] -> B; state B { enter abstract BOn; exit abstract BOff; } }
        }
        state Idle;
        !P -> Idle : /Stop;
    }
    """,
    ["Root.P.POn", "Root.P.POff", "Root.P.R1.A.AOn", "Root.P.R1.A.AOff",
     "Root.P.R2.B.BOn", "Root.P.R2.B.BOff"],
    [[], ["Root.Stop"]],
)

CONTINUATION = (
    """
    state Root {
        event Fin1;
        event Fin2;
        [*] -> Owner;
        state Owner {
            during before abstract Pre;
            during after abstract Post;
            region R1 {
                [*] -> C;
                state C {
                    enter abstract COn;
                    [*] -> L;
                    state L;
                    L -> [*] : /Fin1;
                }
                C -> [*];
            }
            region R2 { [*] -> S; state S; S -> [*] : /Fin2; }
        }
        state Next { during abstract NextWork; }
        Owner -> Next;
    }
    """,
    ["Root.Owner.Pre", "Root.Owner.Post", "Root.Owner.R1.C.COn", "Root.Next.NextWork"],
    [[], ["Root.Fin1"], ["Root.Fin2"], []],
)


FINISHING_REGION_ASPECT = (
    """
    state Root {
        event Stop;
        >> during after abstract RootAfter;
        region A {
            >> during after abstract AAfter;
            [*] -> P;
            state P { during abstract PWork; }
            P -> [*] : /Stop;
        }
        region B { [*] -> Q; state Q { during abstract QWork; } }
    }
    """,
    ["Root.RootAfter", "Root.A.AAfter", "Root.A.P.PWork", "Root.B.Q.QWork"],
    [[], ["Root.Stop"], []],
)

NESTED_OWNER_ASPECT = (
    """
    state Root {
        [*] -> Outer;
        state Outer {
            region R1 {
                [*] -> Inner;
                state Inner {
                    >> during before abstract InnerPre;
                    region X { [*] -> X1; state X1 { during abstract XWork; } }
                    region Y { [*] -> Y1; state Y1 { during abstract YWork; } }
                }
            }
            region R2 { [*] -> S; state S { during abstract SWork; } }
        }
    }
    """,
    [
        "Root.Outer.R1.Inner.InnerPre",
        "Root.Outer.R1.Inner.X.X1.XWork",
        "Root.Outer.R1.Inner.Y.Y1.YWork",
        "Root.Outer.R2.S.SWork",
    ],
    [[], [], []],
)

NESTED_REGION_AFTER_ASPECT = (
    """
    state Root {
        [*] -> Outer;
        state Outer {
            region R1 {
                [*] -> Inner;
                state Inner {
                    region X {
                        >> during after abstract XAfter;
                        [*] -> X1;
                        state X1 { during abstract XWork; }
                    }
                    region Y { [*] -> Y1; state Y1; }
                }
            }
            region R2 { [*] -> S; state S; }
        }
    }
    """,
    ["Root.Outer.R1.Inner.X.XAfter", "Root.Outer.R1.Inner.X.X1.XWork"],
    [[], [], []],
)

DONE_SIBLING_BEFORE_NESTED_ASPECT = (
    """
    state Root {
        event Stop;
        region A { [*] -> P; state P; P -> [*] : /Stop; }
        region B {
            [*] -> Inner;
            state Inner {
                region X {
                    >> during after abstract XAfter;
                    [*] -> X1;
                    state X1 { during abstract XWork; }
                }
                region Y { [*] -> Y1; state Y1; }
            }
        }
    }
    """,
    ["Root.B.Inner.X.XAfter", "Root.B.Inner.X.X1.XWork"],
    [[], ["Root.Stop"], [], []],
)

SINGLE_REGION_OWNER_BELOW_ASPECT = (
    """
    state Root {
        region A {
            >> during after abstract AAfter;
            [*] -> Inner;
            state Inner {
                region Z { [*] -> Z1; state Z1 { during abstract ZWork; } }
            }
        }
        region B { [*] -> Q; state Q; }
    }
    """,
    ["Root.A.AAfter", "Root.A.Inner.Z.Z1.ZWork"],
    [[], [], []],
)

AFTER_ASPECT_ABOVE_THE_GROUP = (
    """
    state Root {
        >> during after abstract RootAfter;
        [*] -> Run;
        state Run {
            region A { [*] -> P; state P; }
            region B { [*] -> Q; state Q; }
        }
    }
    """,
    ["Root.RootAfter"],
    [[], []],
)

AFTER_ASPECT_OF_A_COMPOSITE = (
    """
    state Root {
        [*] -> Run;
        state Plain {
            >> during after abstract PlainAfter;
            [*] -> L;
            state L;
        }
        state Run {
            region A {
                >> during after abstract ACompositeAfter;
                [*] -> C;
                state C { >> during after abstract CAfter; [*] -> L1; state L1; }
            }
            region B { [*] -> Q; state Q; }
        }
    }
    """,
    ["Root.Run.A.ACompositeAfter", "Root.Run.A.C.CAfter"],
    [[], []],
)

FLOAT_SNAPSHOT = (
    """
    def float level = 0.5;
    state Root {
        region A { [*] -> P; state P { during { level = level * 3.0; } during abstract Probe; } }
        region B { [*] -> Q; state Q; }
    }
    """,
    ["Root.A.P.Probe"],
    [[], []],
)


@pytest.mark.parametrize(
    "text, actions, cycles",
    [
        WRAPPED_SCOPES,
        AFTER_ASPECTS,
        NESTED_GROUP,
        FORCED_EXIT,
        CONTINUATION,
        FINISHING_REGION_ASPECT,
        NESTED_OWNER_ASPECT,
        NESTED_REGION_AFTER_ASPECT,
        DONE_SIBLING_BEFORE_NESTED_ASPECT,
        SINGLE_REGION_OWNER_BELOW_ASPECT,
        AFTER_ASPECT_ABOVE_THE_GROUP,
        AFTER_ASPECT_OF_A_COMPOSITE,
        FLOAT_SNAPSHOT,
    ],
    ids=[
        "wrapped_scopes",
        "after_aspects",
        "nested_group",
        "forced_exit",
        "continuation",
        "finishing_region_aspect",
        "nested_owner_aspect",
        "nested_region_after_aspect",
        "done_sibling_before_nested_aspect",
        "single_region_owner_below_aspect",
        "after_aspect_above_the_group",
        "after_aspect_of_a_composite",
        "float_snapshot",
    ],
)
def test_the_calls_of_every_cycle_match_what_the_simulator_reports(
    text, actions, cycles
):
    wanted = simulated_calls(text, actions, cycles)
    assert any(wanted), "the model must make calls for the comparison to mean anything"
    assert decoded_calls(text, cycles) == wanted


def test_a_call_in_the_group_entry_sees_the_regions_that_have_not_started():
    text, actions, cycles = WRAPPED_SCOPES
    calls = decoded_calls(text, cycles)
    entry = calls[1]
    assert [call["configuration"] for call in entry] == [
        "Controller.Running{Safety: Normal, Motion: [init]}",
    ] * 4


def test_an_aspect_over_a_group_reports_the_owner_and_over_a_region_its_leaf():
    text, actions, cycles = WRAPPED_SCOPES
    calls = {call["action"]: call for call in decoded_calls(text, cycles)[1]}
    assert calls["Controller.Tick"]["state"] == "Controller.Running"
    assert calls["Controller.Running.GroupPre"]["state"] == "Controller.Running"
    assert (
        calls["Controller.Running.Safety.SafetyPre"]["state"]
        == "Controller.Running.Safety.Normal"
    )


def test_a_cycle_that_ends_in_a_delta_makes_no_call():
    text = """
    input int g;
    state Root {
        region R1 { [*] -> X; state X { enter abstract XOn; } }
        region R2 { [*] -> Y : if [g != 0]; state Y; }
    }
    """
    model = load_state_machine_from_text(text)
    core = build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= 1: terminated();")
    )
    solver = z3.Solver()
    solver.add(core.core, core.symbols.step_inputs[0]["g"] == 0)
    assert solver.check() == z3.sat
    assert trace_region_step(core, solver.model(), 0).calls == ()


def test_a_core_formula_without_regions_cannot_be_decoded():
    model = load_state_machine_from_text("state Root { state A; [*] -> A; }")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= 1: terminated();")
    )
    solver = z3.Solver()
    solver.add(core.core)
    assert solver.check() == z3.sat
    with pytest.raises(BmcError, match="no regions"):
        trace_region_step(core, solver.model(), 0)


def test_a_cycle_the_formula_does_not_have_cannot_be_decoded():
    model = load_state_machine_from_text(
        "state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }"
    )
    core = build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= 1: terminated();")
    )
    solver = z3.Solver()
    solver.add(core.core)
    assert solver.check() == z3.sat
    with pytest.raises(BmcError, match="not a cycle"):
        trace_region_step(core, solver.model(), 3)


def _core_without_regions():
    model = load_state_machine_from_text("state Root { state A; [*] -> A; }")
    return build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= 1: terminated();")
    )


def test_the_error_analysis_of_a_core_formula_without_regions_cannot_be_built():
    from pyfcstm.bmc.region_relation import region_error_analysis

    with pytest.raises(BmcError, match="no regions"):
        region_error_analysis(_core_without_regions())


def test_the_configuration_of_a_frame_needs_regions_and_a_state():
    from pyfcstm.bmc.region_witness import frame_configuration

    with pytest.raises(BmcError, match="no regions"):
        solver = z3.Solver()
        core = _core_without_regions()
        solver.add(core.core)
        assert solver.check() == z3.sat
        frame_configuration(core, solver.model(), 0)
    model = load_state_machine_from_text(
        "state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }"
    )
    core = build_bmc_core_formula(
        BmcEngine(model).prepare("check reach <= 1: terminated();")
    )
    solver = z3.Solver()
    solver.add(core.core)
    assert solver.check() == z3.sat
    solved = solver.model()
    from pyfcstm.bmc.region_witness import frame_configuration

    assert frame_configuration(core, solved, 0) is None
    assert frame_configuration(core, solved, 1) == "Root{A: P, B: Q}"


def test_a_cycle_is_summed_up_as_one_kind():
    from pyfcstm.bmc.region_witness import RegionStepSummary, RegionStepTrace

    summary = RegionStepSummary(
        0, RegionStepTrace((), ()), (), (), (), (), (), z3.BoolVal(True)
    )
    assert summary.kind(False, False, True) == "absorb"
    assert summary.kind(True, False, False) == "delta"
    assert summary.kind(False, True, False) == "fallback"
    assert summary.kind(False, False, False) == "initial"
    moved = RegionStepSummary(
        0,
        RegionStepTrace((), ()),
        (("Root.A", "transition", "Root.A.P::transition::Root.A.Q::0"),),
        (),
        (),
        (),
        (),
        z3.BoolVal(True),
    )
    assert moved.kind(False, False, False) == "transition"

