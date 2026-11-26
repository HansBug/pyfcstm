from pyfcstm.model import Configuration
from region_trace import load, make_runtime

model = load("controller.fcstm")
for text, mode in [
    ("Controller.Running{Safety: Watching, Motion: On}", "stable"),
    ("Controller.Running{Safety: [done], Motion: On}", "stable"),
    ("Controller.Running{Safety: [init], Motion: [init]}", "initialization"),
    ("Controller.Running", "stable"),
    ("Controller.Running{Safety: [done], Motion: [done]}", "stable"),
]:
    print("parse(%r, mode=%r)" % (text, mode))
    try:
        config = Configuration.parse(model, text, mode=mode)
    except ValueError as error:
        print("  ValueError:", error)
        continue
    print("  repr:  ", repr(config))
    print("  leaves:", [".".join(state.path) for state in config.leaves])

config = Configuration.parse(model, "Controller.Running{Safety: [done], Motion: On}")
print("is_active:", {name: config.is_active(name) for name in ("Controller.Running", "Controller.Running.Safety.Watching", "Controller.Running.Motion.On")})

runtime = make_runtime("controller.fcstm")
print("before the first cycle:", repr(runtime.configuration))
runtime.cycle([], inputs={"fault": 0, "requested": 1})
print("after the first cycle: ", repr(runtime.configuration))
print("type of current_state:", type(runtime.current_state).__name__)
