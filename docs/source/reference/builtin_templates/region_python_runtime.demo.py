import importlib.util
import os
import subprocess
import sys
import tempfile


def generate(model, template, out):
    subprocess.run(
        [sys.executable, "-m", "pyfcstm", "generate", "-i", model,
         "--template", template, "-o", out, "--clear"],
        check=True, stdout=subprocess.DEVNULL,
    )


def load(out, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(out, "machine.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory() as work:
    # --- a model with regions ---
    out = os.path.join(work, "controller")
    generate("region_controller.fcstm", "python", out)
    mod = load(out, "controller_machine")
    machine = mod.ControllerMachine()
    sensors = {"fault": 0, "requested": 1}
    print("== controller: cold start, then cycles")
    machine.cycle(inputs=sensors)
    print("first cycle:", machine.configuration)
    machine.cycle("/Start", inputs=sensors)
    print("after /Start:", machine.configuration)
    machine.cycle(inputs=sensors)
    print("next cycle:", machine.configuration)
    print("motor:", machine.vars["motor"])
    print("leaves:", machine.leaves)
    print("is_active(Controller.Running):", machine.is_active("Controller.Running"))
    print("is_active(Controller.Idle):", machine.is_active("Controller.Idle"))
    for path in ("Controller.Running.Safety", "Controller.Running.Motion"):
        print("region_status(%s): %s" % (path, machine.region_status(path)))
    machine.cycle("/Stop", inputs=sensors)
    print("== after /Stop")
    print("configuration:", machine.configuration)
    print("region_status(Controller.Running.Safety):",
          machine.region_status("Controller.Running.Safety"))
    print("hidden variable __forced_0:", machine.vars["__forced_0"])

    print("== controller: attributes that do not exist")
    try:
        machine.current_state_path
    except AttributeError as err:
        print("AttributeError:", err)
    try:
        machine.region_status("Controller.Idle")
    except ValueError as err:
        print("ValueError:", err)
    try:
        machine.region_status("Controller.Nowhere")
    except ValueError as err:
        print("ValueError:", err)

    print("== controller: initial_state spellings")
    base_vars = {"permit": 0, "motor": 0, "__forced_0": 0}
    spellings = [
        ("configuration text", "Controller.Running{Safety: Watching, Motion: On}"),
        ("text, region left out", "Controller.Running{Motion: On}"),
        ("text, region [init]", "Controller.Running{Safety: Watching, Motion: [init]}"),
        ("dotted path through a region", "Controller.Running.Motion.On"),
        ("owner path only", "Controller.Running"),
        ("tuple", ("Controller", "Running", "Motion", "On")),
    ]
    for label, state in spellings:
        m = mod.ControllerMachine(initial_state=state, initial_vars=dict(base_vars))
        print("%s: %s | Safety=%s Motion=%s" % (
            label, m.configuration,
            m.region_status("Controller.Running.Safety"),
            m.region_status("Controller.Running.Motion")))
    try:
        mod.ControllerMachine(
            initial_state="Controller.Running{Safety: [done], Motion: [done]}",
            initial_vars=dict(base_vars))
    except ValueError as err:
        print("ValueError:", err)

    # --- hook context ---
    print("== probe: hook context")
    out = os.path.join(work, "probe")
    generate("region_probe.fcstm", "python", out)
    mod = load(out, "probe_machine")

    class Probe(mod.LineMachine):
        def read_fault(self):
            return 0

        def _log(self, name, ctx):
            print("%s: state_path=%s active_leaf=%s configuration=%s" % (
                name, ".".join(ctx.state_path), ".".join(ctx.active_leaf),
                ctx.configuration))

        def _abstract_hook_Line_Boot(self, ctx):
            self._log("Boot", ctx)

        def _abstract_hook_Line_Work_Left_L_Tick(self, ctx):
            self._log("Tick", ctx)

        def _abstract_hook_Line_Work_Settle(self, ctx):
            self._log("Settle", ctx)

    probe = Probe()
    probe.cycle()
    print("cycle 1 configuration:", probe.configuration)
    probe.cycle()

    # --- a model without regions ---
    print("== plain: no regions")
    out = os.path.join(work, "plain")
    generate("region_plain.fcstm", "python", out)
    mod = load(out, "plain_machine")
    plain = mod.PlainMachine()
    plain.cycle()
    print("current_state_path:", plain.current_state_path)
    print("current_state_name:", plain.current_state_name)
    print("configuration:", plain.configuration)
    print("leaves:", plain.leaves)
    print("has region_status:", hasattr(plain, "region_status"))
