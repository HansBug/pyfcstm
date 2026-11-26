from region_trace import make_runtime, play

ready = {"fault": 0, "requested": 1}
variables = {"permit": 1, "motor": 0, "__forced_0": 0}


def start(text, given=variables, cycles=1):
    print("initial_state=%r" % text)
    try:
        runtime = make_runtime("controller.fcstm", initial_state=text, initial_vars=given)
    except ValueError as error:
        print("  ValueError:", error)
        print()
        return
    print("  before the first cycle:", runtime.configuration)
    play(runtime, [(None, ready)] * cycles, trace=True, show=["permit", "motor"])
    print()


start("Controller.Running{Safety: Watching, Motion: Off}")
start("Controller.Running{Safety: [done], Motion: On}")
start("Controller.Running.Motion.On")
start("Controller.Running")
start("Controller.Running{Safety: [done], Motion: [done]}")
start("Controller.Running{Safety: Watching, Motion: Off}", given={"permit": 1, "motor": 0})
