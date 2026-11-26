from pyfcstm.model import Configuration
from region_trace import load, make_runtime, table

model = load("active_lowering.fcstm")
print("the machine that runs: to_ast_node() of the model")
print(model.to_ast_node())
print()
print("active_variables() computes the flags of a position")
for text in ("Root.P{A: A1, B: B1}", "Root.P{A: A2, B: B1}"):
    print("  %-24s %s" % (text, model.active_variables(Configuration.parse(model, text))))
print()
runtime = make_runtime("active_lowering.fcstm")
table(runtime, [(None, {}), (["Root.P.A.A1.Go"], {}), (None, {})], show=["__active_Root_P_A_A2"])
