from pyfcstm.model import load_state_machine_from_text
from region_trace import load, make_runtime, play, table

print("forced_condition.fcstm as written")
with open("forced_condition.fcstm", encoding="utf-8") as stream:
    print(stream.read().rstrip())
print()
print("the machine that runs: to_ast_node() of the same model")
print(load("forced_condition.fcstm").to_ast_node())
print()
print("forced_condition.fcstm: the guard becomes true while the regions work")
play(make_runtime("forced_condition.fcstm"), [(None, {})] * 4, trace=True, show=["x", "__forced_0"])
print()
print("controller.fcstm: !Running -> Idle : /Stop takes both regions away")
runtime = make_runtime("controller.fcstm")
ok = {"fault": 0, "requested": 1}
play(runtime, [(None, ok), (["/Start"], ok), (None, ok)], show=["permit", "motor", "__forced_0"])
play(runtime, [(["/Stop"], ok)], trace=True, show=["permit", "motor", "__forced_0"])
print()
print("forced_nested.fcstm: nested owners leave in declaration order")
play(make_runtime("forced_nested.fcstm"), [(None, {}), (["Root.Halt"], {})], trace=True)
