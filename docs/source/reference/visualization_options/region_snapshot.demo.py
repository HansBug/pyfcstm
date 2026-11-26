from pyfcstm.model import load_state_machine_from_text

with open("region_pipeline.fcstm", encoding="utf-8") as f:
    model = load_state_machine_from_text(f.read())
data = model.diagram().to_dict()


def walk(node, depth=0):
    kind = "region" if node.get("region") else "state"
    extra = " ordinal=%d" % node["ordinal"] if node.get("region") else ""
    print("%s%s %s id=%s%s" % ("  " * depth, kind, node["name"], node["id"], extra))
    for child in node["children"]:
        walk(child, depth + 1)


walk(data["rootState"])
pack = data["rootState"]["children"][1]["children"][1]
print("guard:", pack["transitions"][1]["guardLabel"])
print("intake actions:", [a["label"] for a in data["rootState"]["children"][1]["children"][0]["actions"]])
print("work actions:", [a["label"] for a in data["rootState"]["children"][1]["actions"]])
view = model.diagram().with_view_state(collapsed_state_ids=("Line.Work.Intake",)).view_state
print(view)
work = data["rootState"]["children"][1]
print("Work keys:", sorted(k for k in work if k in ("region", "ordinal")))
print("Intake keys:", sorted(k for k in work["children"][0] if k in ("region", "ordinal")))
