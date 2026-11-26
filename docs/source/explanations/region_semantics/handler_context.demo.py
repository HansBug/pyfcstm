from region_trace import make_runtime


def report(name):
    def handler(context):
        def short(path):
            return ".".join(path[1:]) or path[0]

        print(
            "  %-9s state_path=%-22s active_leaf=%-22s configuration=%s"
            % (name, short(context.state_path), short(context.active_leaf), str(context.configuration).replace("Controller.", ""))
        )

    return handler


runtime = make_runtime("handler_context.fcstm")
for action in [
    "Controller.Tick",
    "Controller.Running.GroupPre",
    "Controller.Running.Safety.SafetyPre",
    "Controller.Running.Safety.Normal.Watch",
    "Controller.Running.Motion.On.Drive",
]:
    runtime.register_abstract_handler(action, report(action.split(".")[-1]))

ready = {"fault": 0, "requested": 1}
for events in (None, ["/Start"], None):
    print("cycle %d, events %s" % (runtime.cycle_count + 1, events or "-"))
    runtime.cycle(events, inputs=ready)
    print("  =>", runtime.configuration)
