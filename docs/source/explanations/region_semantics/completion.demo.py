from region_trace import make_runtime, table

wait = {"proceed": 0}
go = {"proceed": 1}
shown = ["a", "b", "aexit", "w"]

print("job_join.fcstm: both regions finish, the owner continues in the same cycle")
table(
    make_runtime("job_join.fcstm"),
    [(None, wait), (["Workflow.ADone"], wait), (None, wait), (["Workflow.BDone"], wait), (None, wait), (None, go)],
    show=shown,
)
print()
print("job_rejected.fcstm: the last completion is refused while the continuation cannot commit")
table(
    make_runtime("job_rejected.fcstm"),
    [(None, wait), (["Workflow.ADone"], wait), (["Workflow.BDone"], wait), (None, go), (["Workflow.BDone"], go)],
    show=shown,
)
print()
print("nested_join.fcstm: an inner group finishes while an outer sibling keeps working")
table(
    make_runtime("nested_join.fcstm"),
    [(None, {}), (["Root.D1"], {}), (["Root.D2"], {}), (None, {})],
)
print()
print("nested_rejected.fcstm: the inner group may finish only if every level above can continue")
table(
    make_runtime("nested_rejected.fcstm"),
    [
        (None, {"ok1": 0, "ok2": 0}),
        (["Root.Finish"], {"ok1": 1, "ok2": 0}),
        (["Root.Finish"], {"ok1": 0, "ok2": 1}),
        (["Root.Finish"], {"ok1": 1, "ok2": 1}),
    ],
)
