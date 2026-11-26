import json
import sys


def walk(state, depth=0):
    marker = "  (region)" if state.get("region") else ""
    print("  " * depth + state["qualifiedName"] + marker)
    for child in state["children"]:
        walk(child, depth + 1)


walk(json.load(sys.stdin)["rootState"])
