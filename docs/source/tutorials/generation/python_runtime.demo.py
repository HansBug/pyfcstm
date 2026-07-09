"""Generate and run the Python built-in template for the tutorial."""

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "simple_machine.fcstm"


def load_machine_module(machine_py):
    """Load a generated ``machine.py`` module from an isolated path."""
    spec = importlib.util.spec_from_file_location(
        "generated_simple_machine", str(machine_py)
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def state_text(machine):
    """Return a compact state and variable summary for demo output."""
    return f"{'.'.join(machine.current_state_path)} counter={machine.vars['counter']}"


with tempfile.TemporaryDirectory() as tmp_name:
    tmp = Path(tmp_name)
    output = tmp / "python"
    subprocess.run(
        [
            "pyfcstm",
            "generate",
            "-i",
            str(MODEL),
            "--template",
            "python",
            "-o",
            str(output),
            "--clear",
        ],
        check=True,
    )

    print("generated files:", ", ".join(path.name for path in sorted(output.iterdir())))

    module = load_machine_module(output / "machine.py")
    machine = module.SimpleMachineMachine()
    machine.cycle()
    print("initial:", state_text(machine))

    for label, event in [
        ("after Start", "SimpleMachine.Idle.Start"),
        ("after Stop", "SimpleMachine.Running.Stop"),
        ("after Reset", "SimpleMachine.Stopped.Reset"),
    ]:
        machine.cycle(event)
        print(f"{label}:", state_text(machine))
