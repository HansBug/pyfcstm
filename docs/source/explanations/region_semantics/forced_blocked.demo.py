from region_trace import make_runtime, play, table

print("forced_blocked.fcstm: the target of !P -> Blocked cannot be entered")
runtime = make_runtime("forced_blocked.fcstm")
play(runtime, [(None, {}), (["Root.Stop"], {}), (None, {}), (["Root.Stop"], {})], trace=True)
print()
print("forced_two_declarations.fcstm: the first declaration that is raised holds the group")
table(
    make_runtime("forced_two_declarations.fcstm"),
    [(None, {}), (["Root.Stop"], {}), (None, {}), (["Root.Stop"], {})],
)
