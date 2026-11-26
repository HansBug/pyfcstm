from region_trace import make_runtime, play

runtime = make_runtime("nested_aspects.fcstm")
play(runtime, [(None, {}), (None, {})], trace=True)
