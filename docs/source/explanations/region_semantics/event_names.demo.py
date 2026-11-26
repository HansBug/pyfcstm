from region_trace import make_runtime

both = "Controller.Running{Safety: Watching, Motion: Off}"
one_done = "Controller.Running{Safety: [done], Motion: Off}"


def send(name, start=both):
    runtime = make_runtime("event_names.fcstm", initial_state=start, initial_vars={"trail": 0})
    try:
        result = runtime.cycle([name])
    except ValueError as error:
        print("%-36s refused: %s" % (name, error))
        return
    print("%-36s -> %s  consumed %s" % (name, runtime.configuration, list(result.consumed_events)))


print("both regions work, no region is done")
for name in ["Go", "Trip", "Ping", "Stop", "Reset", "..Stop", "/Running.Stop", "Controller.Running.Motion.Off.Ping"]:
    send(name)
print()
print("Safety is done, so only Motion has an active leaf")
send("Ping", one_done)
