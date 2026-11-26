from region_trace import make_runtime, play

print("owner_actions.fcstm: the lifecycle actions of an owner around its regions")
runtime = make_runtime("owner_actions.fcstm")
play(runtime, [(None, {}), (None, {}), (["Root.Stop"], {})], trace=True, show=["seq"])
print()
print("group_entry.fcstm: a later region that cannot start does not make an earlier region choose again")
runtime = make_runtime("group_entry.fcstm")
play(runtime, [(None, {}), (["Root.Idle.Go"], {})], trace=True)
