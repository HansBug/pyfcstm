import {
    BinaryOp,
    ConditionalOp,
    Expr,
    IfBlock,
    Operation,
    OperationStatement,
    StateMachine,
    UFunc,
    UnaryOp,
    Variable,
} from '../../model/runtime';

export class UseDefGraph {
    readonly edges: Array<[string, string]>;
    readonly dependenciesByTarget: Record<string, string[]>;

    constructor(edges: Array<[string, string]>) {
        this.edges = [...edges].sort(comparePair);
        const deps: Record<string, string[]> = {};
        for (const [source, target] of this.edges) {
            deps[target] = [...(deps[target] ?? []), source];
        }
        this.dependenciesByTarget = {};
        for (const target of Object.keys(deps).sort()) {
            this.dependenciesByTarget[target] = deps[target];
        }
    }

    dependenciesOf(target: string): string[] {
        return this.dependenciesByTarget[target] ?? [];
    }

    affectingVariables(directVariables: Iterable<string>): string[] {
        const direct = new Set(directVariables);
        const seen = new Set(direct);
        const out = new Set<string>();
        const queue = Array.from(direct);
        while (queue.length > 0) {
            const target = queue.shift()!;
            for (const source of this.dependenciesOf(target)) {
                if (seen.has(source)) continue;
                seen.add(source);
                out.add(source);
                queue.push(source);
            }
        }
        return Array.from(out).sort();
    }
}

export function buildUseDefGraph(machine: StateMachine): UseDefGraph {
    const edges = new Set<string>();

    for (const state of machine.allStates) {
        for (const collection of [state.onEnters, state.onDurings, state.onExits, state.onDuringAspects]) {
            for (const action of collection) {
                if (action.isAbstract) continue;
                walkBlock(action.operations ?? [], new Set(), edges);
            }
        }
        for (const transition of state.transitions) {
            walkBlock(transition.effects ?? [], new Set(), edges);
        }
    }

    return new UseDefGraph(Array.from(edges).map(splitEdge));
}

export function collectExprVariables(expr: Expr): string[] {
    const out: string[] = [];
    walkExprCollect(expr, out);
    return Array.from(new Set(out));
}

function walkBlock(
    statements: OperationStatement[],
    enclosingCondVars: Set<string>,
    edges: Set<string>,
): void {
    for (const stmt of statements) {
        if (stmt instanceof Operation) {
            const deps = new Set([...collectExprVariables(stmt.expr), ...enclosingCondVars]);
            for (const source of deps) {
                edges.add(joinEdge(source, stmt.varName));
            }
            continue;
        }
        if (stmt instanceof IfBlock) {
            const accumulated = new Set<string>();
            for (const branch of stmt.branches) {
                const thisCond = new Set(branch.condition ? collectExprVariables(branch.condition) : []);
                const branchEnclosing = new Set([
                    ...enclosingCondVars,
                    ...accumulated,
                    ...thisCond,
                ]);
                walkBlock(branch.statements, branchEnclosing, edges);
                for (const item of thisCond) accumulated.add(item);
            }
        }
    }
}

function walkExprCollect(expr: Expr, out: string[]): void {
    if (expr instanceof Variable) {
        out.push(expr.name);
        return;
    }
    if (expr instanceof UnaryOp || expr instanceof UFunc) {
        walkExprCollect(expr.x, out);
        return;
    }
    if (expr instanceof BinaryOp) {
        walkExprCollect(expr.x, out);
        walkExprCollect(expr.y, out);
        return;
    }
    if (expr instanceof ConditionalOp) {
        walkExprCollect(expr.cond, out);
        walkExprCollect(expr.ifTrue, out);
        walkExprCollect(expr.ifFalse, out);
    }
}

function joinEdge(source: string, target: string): string {
    return `${source}\u0001${target}`;
}

function splitEdge(edge: string): [string, string] {
    const [source, target] = edge.split('\u0001');
    return [source, target];
}

function comparePair(left: [string, string], right: [string, string]): number {
    if (left[0] < right[0]) return -1;
    if (left[0] > right[0]) return 1;
    if (left[1] < right[1]) return -1;
    if (left[1] > right[1]) return 1;
    return 0;
}
