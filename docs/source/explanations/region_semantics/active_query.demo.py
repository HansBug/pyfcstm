from region_trace import make_runtime, table

shown = ["m", "exit_self", "exit_other", "effect_source", "effect_target", "enter_self", "enter_other"]
steps = [(None, {"fault": 0}), (None, {"fault": 1}), (None, {"fault": 1}), (None, {"fault": 1})]

print("active_query.fcstm: Safety is declared before Motion")
table(make_runtime("active_query.fcstm"), steps, show=shown)
print()
print("active_query_swapped.fcstm: Motion is declared before Safety")
table(make_runtime("active_query_swapped.fcstm"), steps, show=shown)
