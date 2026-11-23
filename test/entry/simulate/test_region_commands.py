"""``pyfcstm simulate`` on a model with regions: batch sessions with golden output.

The goldens were read against the model by hand: every position, variable and
event row follows from the semantics of the model, not from what a run printed.
``n`` adds 1, 100 and 10000 for each cycle the leaves ``W1``, ``W2`` and ``In1``
work in; ``seq`` takes one digit for each ``enter`` that ran (``Comp`` is 4) and
one digit for each ``Ping`` effect (``W1`` 1, ``W2`` 2). ``[`` ``init`` ``]``
marks a region that waits for initialization and ``[`` ``done`` ``]`` a finished
one. A line of dashes stands for the rule that separates the commands.
"""

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import pyfcstmcli

pytestmark = pytest.mark.unittest

RULE = "─" * 60

MODEL = """
def int seq = 0;
def int n = 0;
state W {
    event Reset;
    [*] -> Idle;
    state Idle;
    Idle -> Job :: Start;
    state Job {
        event Stop;
        region A {
            [*] -> Q;
            state Q {
                region A1 {
                    [*] -> W1;
                    state W1 { event Ping; during { n = n + 1; } }
                    W1 -> [*] :: Fin;
                    W1 -> W1 :: Ping effect { seq = seq * 10 + 1; }
                }
                region A2 {
                    [*] -> W2;
                    state W2 { event Ping; during { n = n + 100; } }
                    W2 -> W2 :: Ping effect { seq = seq * 10 + 2; }
                }
            }
        }
        region B {
            [*] -> Comp;
            state Comp {
                enter { seq = seq * 10 + 4; }
                [*] -> In1;
                state In1 { event Next; during { n = n + 10000; } }
                state In2 { enter { seq = seq * 10 + 6; } }
                In1 -> In2 :: Next;
            }
        }
    }
    Job -> Idle : Job.Stop;
}
"""


def _session(tmp_path, commands):
    path = tmp_path / "machine.fcstm"
    path.write_text(MODEL, encoding="utf-8")
    result = simulate_entry(
        pyfcstmcli, ["pyfcstm", "simulate", "-i", str(path), "-e", commands]
    )
    return result, result.stdout.replace(RULE, "~")

COLD_RUN_COMMANDS = 'cycle; cycle Start; current; events; cycle Fin; cycle Next; events'

COLD_RUN = """\
~
>>> cycle
~
Cycle: 1
Current State: W.Idle
Variables:
  n = 0
  seq = 0

~
>>> cycle Start
~
Cycle: 2
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 10101
  seq = 4

~
>>> current
~
Cycle: 2
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 10101
  seq = 4

~
>>> events
~
Available Events:
  • Fin (W.Job.A.Q.A1.W1.Fin)
  • W.Job.A.Q.A1.W1.Ping
  • W.Job.A.Q.A2.W2.Ping
  • Next (W.Job.B.Comp.In1.Next)

~
>>> cycle Fin
~
Cycle: 3
Current State: W.Job{A: Q{A1: [done], A2: W2}, B: Comp.In1}
Variables:
  n = 20201
  seq = 4

~
>>> cycle Next
~
Cycle: 4
Current State: W.Job{A: Q{A1: [done], A2: W2}, B: Comp.In2}
Variables:
  n = 20301
  seq = 46

~
>>> events
~
Available Events:
  • Ping (W.Job.A.Q.A2.W2.Ping)
"""

HOT_START_EVERY_FORM_COMMANDS = 'init W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1} n=0 seq=0; cycle; init W.Job n=0 seq=0; cycle; init W.Job{B: Comp.In1} n=0 seq=0; cycle; init W.Job.B.Comp.In1 n=0 seq=0; cycle; init W.Job{A: Q{A1: [done], A2: W2}, B: [init]} n=0 seq=0; cycle; init W.Idle n=0 seq=0; cycle'

HOT_START_EVERY_FORM = """\
~
>>> init W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1} n=0 seq=0
~
Initialized from state: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Cycle: 0
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 0
  seq = 0

~
>>> cycle
~
Cycle: 1
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 10101
  seq = 0

~
>>> init W.Job n=0 seq=0
~
Initialized from state: W.Job
Cycle: 0
Current State: W.Job{A: [init], B: [init]}
Variables:
  n = 0
  seq = 0

~
>>> cycle
~
Cycle: 1
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 10101
  seq = 4

~
>>> init W.Job{B: Comp.In1} n=0 seq=0
~
Initialized from state: W.Job{B: Comp.In1}
Cycle: 0
Current State: W.Job{A: [init], B: Comp.In1}
Variables:
  n = 0
  seq = 0

~
>>> cycle
~
Cycle: 1
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 10101
  seq = 0

~
>>> init W.Job.B.Comp.In1 n=0 seq=0
~
Initialized from state: W.Job.B.Comp.In1
Cycle: 0
Current State: W.Job{A: [init], B: Comp.In1}
Variables:
  n = 0
  seq = 0

~
>>> cycle
~
Cycle: 1
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 10101
  seq = 0

~
>>> init W.Job{A: Q{A1: [done], A2: W2}, B: [init]} n=0 seq=0
~
Initialized from state: W.Job{A: Q{A1: [done], A2: W2}, B: [init]}
Cycle: 0
Current State: W.Job{A: Q{A1: [done], A2: W2}, B: [init]}
Variables:
  n = 0
  seq = 0

~
>>> cycle
~
Cycle: 1
Current State: W.Job{A: Q{A1: [done], A2: W2}, B: Comp.In1}
Variables:
  n = 10100
  seq = 4

~
>>> init W.Idle n=0 seq=0
~
Initialized from state: W.Idle
Cycle: 0
Current State: W.Idle
Variables:
  n = 0
  seq = 0

~
>>> cycle
~
Cycle: 1
Current State: W.Idle
Variables:
  n = 0
  seq = 0
"""

EVENT_NAMES_COMMANDS = 'cycle; cycle Start; events; cycle W.Job.A.Q.A1.W1.Ping; cycle Fin; events'

EVENT_NAMES = """\
~
>>> cycle
~
Cycle: 1
Current State: W.Idle
Variables:
  n = 0
  seq = 0

~
>>> cycle Start
~
Cycle: 2
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 10101
  seq = 4

~
>>> events
~
Available Events:
  • Fin (W.Job.A.Q.A1.W1.Fin)
  • W.Job.A.Q.A1.W1.Ping
  • W.Job.A.Q.A2.W2.Ping
  • Next (W.Job.B.Comp.In1.Next)

~
>>> cycle W.Job.A.Q.A1.W1.Ping
~
Cycle: 3
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 20202
  seq = 41

~
>>> cycle Fin
~
Cycle: 4
Current State: W.Job{A: Q{A1: [done], A2: W2}, B: Comp.In1}
Variables:
  n = 30302
  seq = 41

~
>>> events
~
Available Events:
  • Ping (W.Job.A.Q.A2.W2.Ping)
  • Next (W.Job.B.Comp.In1.Next)
"""

TABLE_OF_CYCLES_COMMANDS = 'cycle; cycle Start; cycle 3; history 2'

TABLE_OF_CYCLES = """\
~
>>> cycle
~
Cycle: 1
Current State: W.Idle
Variables:
  n = 0
  seq = 0

~
>>> cycle Start
~
Cycle: 2
Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}
Variables:
  n = 10101
  seq = 4

~
>>> cycle 3
~
 Cycle                   State                    Delta    n    seq 
--------------------------------------------------------------------
   3    W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}  False  20202   4  
   4    W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}  False  30303   4  
   5    W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}  False  40404   4  

~
>>> history 2
~
 Cycle                   State                    Delta    n    seq 
--------------------------------------------------------------------
   4    W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}  False  30303   4  
   5    W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}  False  40404   4  
"""


@pytest.mark.parametrize(
    ["commands", "golden"],
    [
        pytest.param(COLD_RUN_COMMANDS, COLD_RUN, id="cold-run"),
        pytest.param(
            HOT_START_EVERY_FORM_COMMANDS, HOT_START_EVERY_FORM, id="hot-start-every-form"
        ),
        pytest.param(EVENT_NAMES_COMMANDS, EVENT_NAMES, id="event-names"),
        pytest.param(TABLE_OF_CYCLES_COMMANDS, TABLE_OF_CYCLES, id="table-of-cycles"),
    ],
)
def test_a_batch_session_prints_the_golden_output(tmp_path, commands, golden):
    result, output = _session(tmp_path, commands)
    assert result.exitcode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert output == golden


@pytest.mark.parametrize(
    ["commands", "message"],
    [
        pytest.param(
            "init W.Job{A: [done], B: [done]} n=0 seq=0",
            "All regions are Done at 'W.Job'",
            id="every-region-done",
        ),
        pytest.param(
            "init W.Job{A: Q n=0 seq=0",
            "the braces of the configuration text 'W.Job{A: Q n=0 seq=0' are not balanced",
            id="braces-not-closed",
        ),
        pytest.param(
            "init W.Job{C: Q} n=0 seq=0", "Initialization failed", id="unknown-region"
        ),
        pytest.param(
            "init W.Job n=0",
            "All variables must be provided. Missing: ['seq']",
            id="variable-missing",
        ),
        pytest.param(
            "init W.Nowhere n=0 seq=0", "Unknown configuration path: 'W.Nowhere'", id="unknown-state"
        ),
        pytest.param(
            "init W.Job n=0 seq=0 n=5",
            "variable 'n' is assigned more than once",
            id="variable-given-twice",
        ),
        pytest.param(
            "cycle; cycle Start; cycle Ping",
            "Position-dependent event name 'Ping' is ambiguous: "
            "W.Job.A.Q.A1.W1.Ping (from W.Job.A.Q.A1.W1); "
            "W.Job.A.Q.A2.W2.Ping (from W.Job.A.Q.A2.W2)",
            id="ambiguous-event-name",
        ),
        pytest.param(
            "cycle; cycle Start; cycle Nope",
            "Position-dependent event name 'Nope' matches no event from any active leaf",
            id="unknown-event-name",
        ),
    ],
)
def test_a_command_that_cannot_run_fails_with_its_reason(tmp_path, commands, message):
    result, _ = _session(tmp_path, commands)
    output = result.stdout + result.stderr
    assert result.exitcode == 1
    assert message in output
    assert "Traceback" not in output


def _completer(model_text=MODEL, start_events=("W.Idle.Start",)):
    from prompt_toolkit.document import Document

    from pyfcstm.entry.simulate.commands import CommandProcessor
    from pyfcstm.model import load_state_machine_from_text
    from pyfcstm.simulate import SimulationRuntime

    runtime = SimulationRuntime(load_state_machine_from_text(model_text))
    runtime.cycle()
    for event in start_events:
        runtime.cycle([event])
    completer = CommandProcessor(runtime).create_completer()
    return lambda text: [
        (item.text, item.display_meta_text)
        for item in completer.get_completions(Document(text, len(text)), None)
    ]


@pytest.mark.parametrize("lead", ["", "  ", "\t"])
def test_init_completion_ignores_whitespace_before_the_command(lead):
    complete = _completer()
    assert "W.Job.B.Comp.In1" in [text for text, _ in complete(lead + "init W.Job.B.Comp")]
    assert "seq=" in [text for text, _ in complete(lead + "init W.Job{A: [init], B: Comp.In1} ")]


def test_init_completes_the_states_inside_regions():
    complete = _completer()
    texts = [text for text, _ in complete("init W.Job.B")]
    assert "W.Job.B.Comp" in texts
    assert "W.Job.B.Comp.In1" in texts
    assert "W.Job.B.Comp.In2" in texts
    assert dict(complete("init W.Job.B.Comp"))["W.Job.B.Comp.In1"] == "leaf state"
    assert dict(complete("init W.Job.B.Comp"))["W.Job.B.Comp"] == "composite state"


def test_init_completes_variables_after_a_configuration_text():
    complete = _completer()
    assert "seq=" in [text for text, _ in complete("init W.Job{A: [init], B: Comp.In1} ")]
    # An assigned variable is not offered again; the spaces in the braces do not count.
    after = [text for text, _ in complete("init W.Job{A: [init], B: Comp.In1} seq=1 ")]
    assert "n=" in after and "seq=" not in after


def test_init_completes_nothing_inside_the_braces_of_a_configuration_text():
    complete = _completer()
    assert complete("init W.Job{A: Q") == []
    assert complete("init W.Job{A: Q, ") == []


def test_cycle_completes_the_event_names_that_lead_to_one_event():
    complete = _completer()
    texts = [text for text, _ in complete("cycle ")]
    assert "Fin" in texts and "Next" in texts
    # ``Ping`` belongs to two leaves; only the full paths are offered.
    assert "Ping" not in texts
    assert "W.Job.A.Q.A1.W1.Ping" in texts
    assert "W.Job.A.Q.A2.W2.Ping" in texts


def test_init_accepts_spaces_before_the_opening_brace(tmp_path):
    result, output = _session(
        tmp_path, "init W.Job {A: Q{A1: W1, A2: W2}, B: Comp.In1} n=0 seq=0; cycle"
    )
    assert result.exitcode == 0, result.stdout
    assert "Current State: W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}" in output
    assert "n = 10101" in output


def test_init_ends_the_position_at_the_closing_brace_even_without_a_space(tmp_path):
    result, output = _session(
        tmp_path, "init W.Job{A: Q{A1: W1, A2: W2}, B: Comp.In1}n=0 seq=0; cycle"
    )
    assert result.exitcode == 0, result.stdout
    assert "n = 10101" in output


OWNER_EVENT_MODEL = """
state Root {
    [*] -> Run;
    state Run {
        event Stop;
        region A {
            [*] -> X;
            state X { event Go; }
            X -> X :: Go;
            X -> X : /Run.Stop;
        }
        region B { [*] -> Y; state Y; Y -> Y : /Run.Stop; }
    }
}
"""


def test_events_show_a_short_name_only_when_typing_it_works(tmp_path):
    """``Go`` belongs to the leaf; ``Stop`` belongs to the owner above both leaves."""
    path = tmp_path / "owner.fcstm"
    path.write_text(OWNER_EVENT_MODEL, encoding="utf-8")
    result = simulate_entry(
        pyfcstmcli, ["pyfcstm", "simulate", "-i", str(path), "-e", "cycle; events; cycle Go; cycle Stop"]
    )
    assert "  • Go (Root.Run.A.X.Go)" in result.stdout
    assert "  • Root.Run.Stop\n" in result.stdout
    assert "(Root.Run.Stop)" not in result.stdout
    # The list told the truth: ``Go`` was accepted and ``Stop`` is not a name from here.
    assert "Cycle: 2" in result.stdout
    assert result.exitcode == 1
    assert "matches no event from any active leaf" in result.stdout


def test_completion_offers_a_short_name_only_when_typing_it_works():
    complete = _completer(OWNER_EVENT_MODEL, start_events=())
    texts = [text for text, _ in complete("cycle ")]
    assert "Go" in texts and "Root.Run.Stop" in texts
    assert "Stop" not in texts
