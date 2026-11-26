from region_trace import make_runtime, play

runtime = make_runtime("controller.fcstm")
ready = {"fault": 0, "requested": 1}
steps = [
    (None, ready),
    (["/Start"], ready),
    (None, ready),
    (None, {"fault": 1, "requested": 1}),
]
play(runtime, steps, trace=True, show=["permit", "motor"])
