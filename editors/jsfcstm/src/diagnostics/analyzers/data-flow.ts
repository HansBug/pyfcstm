import type {ModelDiagnosticJson, VariableInfo} from '../inspect';

export function collectDataFlowWarnings(
    variables: VariableInfo[],
    reachabilityGraph: Record<string, string[]>,
): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    out.push(...guardVarsNeverChangeDiagnostics(variables));
    for (const variable of variables) {
        out.push(...variableUsageDiagnostics(variable, reachabilityGraph));
    }
    return out;
}

function variableUsageDiagnostics(
    variable: VariableInfo,
    reachabilityGraph: Record<string, string[]>,
): ModelDiagnosticJson[] {
    const readStates = variableReadStates(variable);
    const writeStates = variableWriteStates(variable);
    if (readStates.size === 0 && writeStates.size === 0) {
        return [unreferencedVarDiagnostic(variable)];
    }
    if (readStates.size > 0 && writeStates.size === 0) {
        return [unwrittenReadVarDiagnostic(variable, readStates)];
    }
    if (writeStates.size > 0 && readStates.size === 0) {
        return [writeOnlyVarDiagnostic(variable, writeStates)];
    }

    const finalWrites = finalWriteLocations(variable, readStates, reachabilityGraph);
    if (finalWrites.length === 0) return [];
    return [{
        code: 'W_VARIABLE_NEVER_READ_AFTER_FINAL_WRITE',
        severity: 'warning',
        message: `Variable ${JSON.stringify(variable.name)} has final write sites with no reachable later read.`,
        span: null,
        refs: {
            var_name: variable.name,
            write_locations: finalWrites,
        },
    }];
}

function variableReadStates(variable: VariableInfo): Set<string> {
    const readStates = new Set(variable.read_in_states);
    for (const [source] of variable.read_in_guards) readStates.add(source);
    return readStates;
}

function variableWriteStates(variable: VariableInfo): Set<string> {
    const writeStates = new Set(variable.written_in_states);
    for (const [source] of variable.written_in_effects) writeStates.add(source);
    return writeStates;
}

function unreferencedVarDiagnostic(variable: VariableInfo): ModelDiagnosticJson {
    if (variable.abstract_actions_in_scope.length > 0) {
        return {
            code: 'I_UNREFERENCED_VAR_MAYBE_ABSTRACT',
            severity: 'info',
            message: `Variable ${JSON.stringify(variable.name)} is unused in DSL statements, but abstract actions may use it externally.`,
            span: null,
            refs: {
                var_name: variable.name,
                abstract_actions_in_scope: variable.abstract_actions_in_scope,
            },
        };
    }
    return {
        code: 'W_UNREFERENCED_VAR',
        severity: 'warning',
        message: `Variable ${JSON.stringify(variable.name)} is never read or written.`,
        span: null,
        refs: {
            var_name: variable.name,
            init_value: variable.init_value,
        },
    };
}

function unwrittenReadVarDiagnostic(variable: VariableInfo, readStates: Set<string>): ModelDiagnosticJson {
    return {
        code: 'W_UNWRITTEN_READ_VAR',
        severity: 'warning',
        message: `Variable ${JSON.stringify(variable.name)} is read but never written by any action or transition effect.`,
        span: null,
        refs: {
            var_name: variable.name,
            read_states: Array.from(readStates).sort(),
            init_value: variable.init_value,
        },
    };
}

function writeOnlyVarDiagnostic(variable: VariableInfo, writeStates: Set<string>): ModelDiagnosticJson {
    return {
        code: 'W_WRITE_ONLY_VAR',
        severity: 'warning',
        message: `Variable ${JSON.stringify(variable.name)} is written but never read.`,
        span: null,
        refs: {
            var_name: variable.name,
            written_states: Array.from(writeStates).sort(),
        },
    };
}

function guardVarsNeverChangeDiagnostics(variables: VariableInfo[]): ModelDiagnosticJson[] {
    const writesByVar: Record<string, Set<string>> = {};
    for (const variable of variables) {
        writesByVar[variable.name] = variableWriteStates(variable);
    }
    const guardVars = new Map<string, {edge: [string, string]; names: Set<string>}>();
    for (const variable of variables) {
        for (const edge of variable.read_in_guards) {
            const key = `${edge[0]}\u0001${edge[1]}`;
            const item = guardVars.get(key) ?? {edge, names: new Set<string>()};
            item.names.add(variable.name);
            guardVars.set(key, item);
        }
    }

    const out: ModelDiagnosticJson[] = [];
    const items = Array.from(guardVars.values()).sort((a, b) => {
        const left = `${a.edge[0]}\u0001${a.edge[1]}`;
        const right = `${b.edge[0]}\u0001${b.edge[1]}`;
        return left.localeCompare(right);
    });
    for (const {edge, names} of items) {
        const neverChanged = Array.from(names)
            .filter(name => (writesByVar[name]?.size ?? 0) === 0)
            .sort();
        if (neverChanged.length !== names.size) continue;
        out.push({
            code: 'W_GUARD_VARS_NEVER_CHANGE',
            severity: 'warning',
            message: `Transition ${JSON.stringify(edge[0])} -> ${JSON.stringify(edge[1])} guard only reads variables that never change.`,
            span: null,
            refs: {
                transition_span: null,
                guard_vars: neverChanged,
            },
        });
    }
    return out;
}

function finalWriteLocations(
    variable: VariableInfo,
    readStates: Set<string>,
    reachabilityGraph: Record<string, string[]>,
): string[] {
    const out: string[] = [];
    for (const statePath of variable.written_in_states) {
        if (!hasReachableRead(statePath, readStates, reachabilityGraph)) {
            out.push(statePath);
        }
    }
    for (const [fromPath, toPath] of variable.written_in_effects) {
        if (toPath !== '[*]' && hasReachableRead(toPath, readStates, reachabilityGraph)) {
            continue;
        }
        out.push(`${fromPath}->${toPath}`);
    }
    return Array.from(new Set(out)).sort();
}

function hasReachableRead(
    startPath: string,
    readStates: Set<string>,
    reachabilityGraph: Record<string, string[]>,
): boolean {
    if (readStates.has(startPath)) return true;
    for (const reachable of reachabilityGraph[startPath] ?? []) {
        if (readStates.has(reachable)) return true;
    }
    return false;
}
