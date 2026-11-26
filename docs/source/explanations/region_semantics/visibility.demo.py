from region_trace import make_runtime, table

print("visible_forward.fcstm: the writer is declared first")
table(make_runtime("visible_forward.fcstm"), [(None, {})] * 3)
print()
print("visible_backward.fcstm: the reader is declared first")
table(make_runtime("visible_backward.fcstm"), [(None, {})] * 3)
print()
print("multi_writer.fcstm: three regions write x and y")
table(make_runtime("multi_writer.fcstm"), [(None, {})] * 3)
print()
print("sampled_once.fcstm: two regions read the same input k")
table(make_runtime("sampled_once.fcstm"), [(None, {"k": 2}), (None, {"k": 3})])
