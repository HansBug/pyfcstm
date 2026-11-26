from region_trace import make_runtime, play, table

ok = {"fault": 0, "requested": 1}
fault = {"fault": 1, "requested": 1}
steps = [(None, ok), (["/Start"], ok), (None, ok), (None, fault), (None, fault), (None, ok), (None, ok)]
shown = ["permit", "motor"]

print("controller.fcstm: Safety is declared before Motion")
table(make_runtime("controller.fcstm"), steps, show=shown)
print()
print("controller_swapped.fcstm: Motion is declared before Safety")
table(make_runtime("controller_swapped.fcstm"), steps, show=shown)
print()
print("controller_swapped.fcstm, the fault cycle in detail")
runtime = make_runtime("controller_swapped.fcstm")
play(runtime, steps[:3], show=shown)
play(runtime, steps[3:4], trace=True, show=shown)
