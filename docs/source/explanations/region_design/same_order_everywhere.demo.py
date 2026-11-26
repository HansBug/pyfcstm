"""Run the swapped controller in the simulator and in the generated Python runtime."""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

MODEL = "controller_swapped.fcstm"
ready = {"fault": 0, "requested": 1}
fault = {"fault": 1, "requested": 1}
steps = [(None, ready), (["/Start"], ready), (None, ready), (None, fault), (None, fault), (None, ready)]

with tempfile.TemporaryDirectory() as out:
    subprocess.run(
        [sys.executable, "-m", "pyfcstm", "generate", "-i", MODEL, "--template", "python", "-o", out],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    spec = importlib.util.spec_from_file_location("generated_machine", Path(out) / "machine.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    simulator = SimulationRuntime(
        load_state_machine_from_text(Path(MODEL).read_text(encoding="utf-8")),
        input_source=ready,
    )
    generated = module.ControllerMachine()
    print("%-5s %-78s %-78s %s" % ("cycle", "simulator", "generated Python", "same"))
    for number, (events, inputs) in enumerate(steps, start=1):
        simulator.cycle(events, inputs=inputs)
        generated.cycle(events, inputs=inputs)
        left = "%s %s" % (simulator.configuration, {k: simulator.vars[k] for k in ("permit", "motor")})
        right = "%s %s" % (generated.configuration, {k: generated.vars[k] for k in ("permit", "motor")})
        print("%-5d %-78s %-78s %s" % (number, left, right, left == right))
