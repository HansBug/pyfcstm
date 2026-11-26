from region_trace import make_runtime, play, table

print("candidate_fallback.fcstm: a candidate that cannot be entered gives way to the next one")
runtime = make_runtime("candidate_fallback.fcstm")
play(runtime, [(None, {})] * 3, trace=True)
print()
print("initial_fallback.fcstm: an initial candidate that fails inside a region leaves nothing behind")
table(make_runtime("initial_fallback.fcstm"), [(None, {})] * 2)
print()
print("group_delta.fcstm, cold start: the second region cannot start")
table(make_runtime("group_delta.fcstm"), [(None, {"g": 0}), (None, {"g": 0}), (None, {"g": 1}), (None, {"g": 1})])
print()
print("group_delta.fcstm, hot start with the second region waiting")
table(
    make_runtime("group_delta.fcstm", initial_state="Root.P{R1: A, R2: [init]}", initial_vars={"n": 0}),
    [(None, {"g": 0}), (None, {"g": 0}), (None, {"g": 1}), (None, {"g": 1})],
)
