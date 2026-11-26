from pyfcstm.model import load_state_machine_from_text

for path in ("forced_composite.fcstm", "forced_regions.fcstm"):
    with open(path, encoding="utf-8") as stream:
        model = load_state_machine_from_text(stream.read())
    print("==", path, "as the machine that runs")
    print(model.to_ast_node())
