set -e
trap 'rm -rf .region_diagram' EXIT
mkdir -p .region_diagram
pyfcstm diagram -i region_controller.fcstm -o .region_diagram/machine.json
python - <<'PY'
import json

data = json.load(open(".region_diagram/machine.json", encoding="utf-8"))


def walk(node, depth=0):
    mark = f"region {node['ordinal']}" if node.get("region") else "state"
    print(f"{'  ' * depth}{node['qualifiedName']} [{mark}]")
    for child in node.get("children", []):
        if isinstance(child, dict):
            walk(child, depth + 1)


walk(data["rootState"])
print(data["summary"])
PY
