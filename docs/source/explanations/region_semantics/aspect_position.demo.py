from region_trace import make_runtime, play, table

print("aspect_position.fcstm: where the aspects of the root and the owner sit")
table(make_runtime("aspect_position.fcstm"), [(None, {})] * 3)
print()
print("the second cycle in detail")
runtime = make_runtime("aspect_position.fcstm")
play(runtime, [(None, {})], show=["tick"])
play(runtime, [(None, {})], trace=True, show=["tick", "post", "own"])
print()
print("region_aspect.fcstm: an aspect of a region covers only that region and only during work")
table(make_runtime("region_aspect.fcstm"), [(None, {}), (["Root.End1"], {}), (None, {})])
