import type {ActionInfo, ModelDiagnosticJson} from '../inspect';

export function collectNamingWarnings(actions: ActionInfo[]): ModelDiagnosticJson[] {
    const byName = new Map<string, ActionInfo[]>();
    for (const action of actions) {
        if (!action.name || action.is_ref) continue;
        byName.set(action.name, [...(byName.get(action.name) ?? []), action]);
    }

    const out: ModelDiagnosticJson[] = [];
    for (const [functionName, items] of byName.entries()) {
        const sorted = [...items].sort((a, b) => a.state_path.localeCompare(b.state_path));
        for (const inner of sorted) {
            const ancestors = sorted.filter(outer =>
                isStrictAncestor(outer.state_path, inner.state_path)
            );
            if (ancestors.length === 0) continue;
            ancestors.sort((a, b) => b.state_path.length - a.state_path.length);
            const outer = ancestors[0];
            out.push({
                code: 'W_NAMED_ACTION_SHADOWS_ANCESTOR',
                severity: 'warning',
                message: `Named action ${JSON.stringify(functionName)} in ${JSON.stringify(inner.state_path)} shadows ancestor action in ${JSON.stringify(outer.state_path)}.`,
                span: null,
                refs: {
                    function_name: functionName,
                    inner_state_path: inner.state_path,
                    outer_state_path: outer.state_path,
                },
            });
        }
    }
    return out;
}

function isStrictAncestor(outerPath: string, innerPath: string): boolean {
    return outerPath.length > 0 && innerPath.startsWith(`${outerPath}.`);
}
