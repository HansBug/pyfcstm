import z3

from pyfcstm.bmc import compile_bmc_query
from pyfcstm.model import load_state_machine_from_text


def chain_machine(n):
    """A ring of n leaf states; every state has the guards d == 0 and d == 1."""
    lines = ["input int d;", "state Root {", "    [*] -> S0;"]
    lines += ["    state S%d;" % i for i in range(n)]
    for i in range(n):
        lines.append("    S%d -> S%d : if [d == 0];" % (i, (i + 1) % n))
        lines.append("    S%d -> S%d : if [d == 1];" % (i, 0))
    lines.append("}")
    return "\n".join(lines)


def count_nodes(expr):
    """Count the distinct nodes of a z3 expression DAG."""
    seen, stack = set(), [expr]
    while stack:
        node = stack.pop()
        if node.get_id() not in seen:
            seen.add(node.get_id())
            stack.extend(node.children())
    return len(seen)


print("N   k  nodes  21Nk-18N+33k+6  equal")
for n in (8, 12, 16):
    model = load_state_machine_from_text(chain_machine(n))
    for k in (2, 3, 4, 5):
        query = 'check reach <= %d: active("Root.S%d");' % (k, k + 2)
        nodes = count_nodes(compile_bmc_query(model, query).solve_formula)
        closed = 21 * n * k - 18 * n + 33 * k + 6
        print("%-3d %d  %-5d  %-14d  %s" % (n, k, nodes, closed, nodes == closed))
