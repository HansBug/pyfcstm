import type {ModelDiagnosticJson, StateInfo, TransitionInfo, VariableInfo} from '../inspect';

export function collectDataFlowWarnings(
    variables: VariableInfo[],
    reachabilityGraph: Record<string, string[]>,
    states: StateInfo[] = [],
    rootStatePath?: string,
    transitions: TransitionInfo[] = [],
): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    const stateParentPaths = stateParentPathMap(states);
    const exitTransitionSources = collectExitTransitionSources(transitions);
    const {normalEdges, initialEdges} = directReachabilityEdges(states, transitions);
    out.push(...guardVarsNeverChangeDiagnostics(variables));
    for (const variable of variables) {
        out.push(...variableUsageDiagnostics(
            variable,
            reachabilityGraph,
            stateParentPaths,
            rootStatePath,
            exitTransitionSources,
            normalEdges,
            initialEdges,
        ));
    }
    return out;
}

function variableUsageDiagnostics(
    variable: VariableInfo,
    reachabilityGraph: Record<string, string[]>,
    stateParentPaths: Record<string, string | null>,
    rootStatePath?: string,
    exitTransitionSources: Set<string> = new Set(),
    normalEdges: Record<string, Set<string>> = {},
    initialEdges: Record<string, Set<string>> = {},
): ModelDiagnosticJson[] {
    const usageReadStates = variableUsageReadStates(variable);
    const livenessReadStates = variableLivenessReadStates(variable);
    const initialGuardReadEdges = variableInitialGuardReadEdges(variable);
    const effectReadEdges = variableEffectReadEdges(variable);
    const actionReadAfterWriteStages =
        variableActionReadAfterWriteStages(variable);
    const effectReadAfterWriteOccurrences =
        variableEffectReadAfterWriteOccurrences(variable);
    const writeStates = variableWriteStates(variable);
    if (usageReadStates.size === 0 && writeStates.size === 0) {
        return [unreferencedVarDiagnostic(variable)];
    }
    if (usageReadStates.size > 0 && writeStates.size === 0) {
        return [unwrittenReadVarDiagnostic(variable, usageReadStates)];
    }
    if (writeStates.size > 0 && usageReadStates.size === 0) {
        return [writeOnlyVarDiagnostic(variable, writeStates)];
    }

    const finalWrites = finalWriteLocations(
        variable,
        livenessReadStates,
        reachabilityGraph,
        stateParentPaths,
        rootStatePath,
        exitTransitionSources,
        normalEdges,
        initialEdges,
        initialGuardReadEdges,
        effectReadEdges,
        actionReadAfterWriteStages,
        effectReadAfterWriteOccurrences,
    );
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

function stateParentPathMap(states: StateInfo[]): Record<string, string | null> {
    const out: Record<string, string | null> = {};
    for (const state of states) out[state.path] = state.parent_path;
    return out;
}

function collectExitTransitionSources(transitions: TransitionInfo[]): Set<string> {
    return new Set(
        transitions
            .filter(transition => transition.to_path === '[*]')
            .map(transition => transition.from_path),
    );
}

function directReachabilityEdges(
    states: StateInfo[],
    transitions: TransitionInfo[],
): {normalEdges: Record<string, Set<string>>; initialEdges: Record<string, Set<string>>} {
    const normalEdges: Record<string, Set<string>> = {};
    const initialEdges: Record<string, Set<string>> = {};
    for (const state of states) {
        normalEdges[state.path] = new Set<string>();
        initialEdges[state.path] = new Set<string>();
    }
    for (const transition of transitions) {
        if (transition.from_path === '[*]' || transition.to_path === '[*]') continue;
        normalEdges[transition.from_path]?.add(transition.to_path);
    }
    for (const state of states) {
        for (const target of state.initial_targets ?? []) {
            if (target.target !== '[*]') {
                initialEdges[state.path].add(target.target);
            }
        }
    }
    return {normalEdges, initialEdges};
}

function variableUsageReadStates(variable: VariableInfo): Set<string> {
    const readStates = new Set(variable.read_in_states);
    for (const [fromPath, toPath] of guardOccurrences(variable)) {
        readStates.add(guardReadState(fromPath, toPath));
    }
    return readStates;
}

function variableLivenessReadStates(variable: VariableInfo): Set<string> {
    const readStates = new Set(variable.read_in_states);
    for (const [fromPath] of guardOccurrences(variable)) {
        if (fromPath !== '[*]') readStates.add(fromPath);
    }
    return readStates;
}

function guardOccurrences(variable: VariableInfo): Array<[string, string, string]> {
    const occurrences = variable.read_in_guard_occurrences ?? [];
    if (occurrences.length > 0) return occurrences;
    return variable.read_in_guards.map(([fromPath, toPath]) =>
        [fromPath, toPath, `${fromPath}->${toPath}`] as [string, string, string]
    );
}

function guardReadState(fromPath: string, toPath: string): string {
    return fromPath === '[*]' ? toPath : fromPath;
}

function variableInitialGuardReadEdges(variable: VariableInfo): Set<string> {
    const edges = new Set<string>();
    for (const [fromPath, toPath, occurrenceKey] of guardOccurrences(variable)) {
        if (fromPath !== '[*]') continue;
        const owner = initialGuardOwner(occurrenceKey, toPath);
        if (owner !== null) edges.add(edgeKey(owner, toPath));
    }
    return edges;
}

function initialGuardOwner(occurrenceKey: string, targetPath: string): string | null {
    if (occurrenceKey && occurrenceKey.includes('#')) {
        const owner = occurrenceKey.split('#').slice(0, -1).join('#');
        if (owner) return owner;
    }
    const lastDot = targetPath.lastIndexOf('.');
    return lastDot >= 0 ? targetPath.slice(0, lastDot) : null;
}

function edgeKey(fromPath: string, toPath: string): string {
    return `${fromPath}\u0001${toPath}`;
}

function tripleKey(fromPath: string, toPath: string, occurrenceKey: string): string {
    return `${fromPath}\u0001${toPath}\u0001${occurrenceKey}`;
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
    const guardVars = new Map<string, {occurrence: [string, string, string]; names: Set<string>}>();
    for (const variable of variables) {
        const guardOccurrences = variable.read_in_guard_occurrences ?? [];
        const occurrences = guardOccurrences.length > 0
            ? guardOccurrences
            : variable.read_in_guards.map(([fromPath, toPath]) =>
                [fromPath, toPath, `${fromPath}->${toPath}`] as [string, string, string]
            );
        for (const occurrence of occurrences) {
            const key = `${occurrence[0]}\u0001${occurrence[1]}\u0001${occurrence[2]}`;
            const item = guardVars.get(key) ?? {occurrence, names: new Set<string>()};
            item.names.add(variable.name);
            guardVars.set(key, item);
        }
    }

    const out: ModelDiagnosticJson[] = [];
    const emittedRefs = new Set<string>();
    const items = Array.from(guardVars.values()).sort((a, b) => {
        const left = `${a.occurrence[0]}\u0001${a.occurrence[1]}\u0001${a.occurrence[2]}`;
        const right = `${b.occurrence[0]}\u0001${b.occurrence[1]}\u0001${b.occurrence[2]}`;
        return left.localeCompare(right);
    });
    for (const {occurrence, names} of items) {
        const neverChanged = Array.from(names)
            .filter(name => writesByVar[name].size === 0)
            .sort();
        if (neverChanged.length !== names.size) continue;
        const refKey = JSON.stringify([neverChanged, null]);
        if (emittedRefs.has(refKey)) continue;
        emittedRefs.add(refKey);
        out.push({
            code: 'W_GUARD_VARS_NEVER_CHANGE',
            severity: 'warning',
            message: `Transition ${JSON.stringify(occurrence[0])} -> ${JSON.stringify(occurrence[1])} guard only reads variables that never change.`,
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
    stateParentPaths: Record<string, string | null>,
    rootStatePath?: string,
    exitTransitionSources: Set<string> = new Set(),
    normalEdges: Record<string, Set<string>> = {},
    initialEdges: Record<string, Set<string>> = {},
    initialGuardReadEdges: Set<string> = new Set(),
    effectReadEdges: Set<string> = new Set(),
    actionReadAfterWriteStages: Set<string> = new Set(),
    effectReadAfterWriteOccurrences: Set<string> = new Set(),
): string[] {
    const out: string[] = [];
    const actionWrites = actionWriteStages(variable);
    for (const [statePath, stage] of actionWrites) {
        if (
            stage !== null &&
            actionReadAfterWriteStages.has(edgeKey(statePath, stage))
        ) {
            continue;
        }
        const actionReadStates = actionReadStatesAfterWrite(
            variable,
            statePath,
            stage,
            readStates,
        );
        if (hasReachableReadAfterActionWrite(
            statePath,
            stage,
            actionReadStates,
            reachabilityGraph,
            stateParentPaths,
            rootStatePath,
            exitTransitionSources,
            normalEdges,
            initialEdges,
            initialGuardReadEdges,
            effectReadEdges,
        )) {
            continue;
        }
        out.push(statePath);
    }
    for (const [fromPath, toPath, occurrenceKey] of effectWriteOccurrences(variable)) {
        if (
            occurrenceKey !== null &&
            effectReadAfterWriteOccurrences.has(
                tripleKey(fromPath, toPath, occurrenceKey),
            )
        ) continue;
        if (toPath === '[*]') {
            if (hasReachableReadAfterExitEffect(
                fromPath,
                readStates,
                reachabilityGraph,
                stateParentPaths,
                rootStatePath,
                normalEdges,
                initialEdges,
                initialGuardReadEdges,
            )) continue;
        } else if (hasReachableRead(
            toPath,
            readStates,
            reachabilityGraph,
            normalEdges,
            initialEdges,
            initialGuardReadEdges,
        )) continue;
        out.push(`${fromPath}->${toPath}`);
    }
    return Array.from(new Set(out)).sort();
}

function actionWriteStages(variable: VariableInfo): Array<[string, string | null]> {
    const actionStages = variable.written_in_action_stages ?? [];
    if (actionStages.length > 0) {
        return actionStages;
    }
    return variable.written_in_states.map(statePath => [statePath, null]);
}

const ACTION_STAGE_ORDER: Record<string, number> = {
    enter: 0,
    during: 1,
    during_aspect: 1,
    exit: 2,
};

function actionReadStatesAfterWrite(
    variable: VariableInfo,
    statePath: string,
    stage: string | null,
    readStates: Set<string>,
): Set<string> {
    if (
        stage === null ||
        stage !== 'enter' ||
        sameStateReadCanFollowActionWrite(
            variable,
            statePath,
            stage,
        )
    ) {
        return readStates;
    }
    const filtered = new Set(readStates);
    filtered.delete(statePath);
    return filtered;
}

function sameStateReadCanFollowActionWrite(
    variable: VariableInfo,
    statePath: string,
    stage: string,
): boolean {
    for (const [readState, readStage] of variable.read_in_action_stages ?? []) {
        if (readState === statePath && actionStageIsAfter(readStage, stage)) {
            return true;
        }
    }
    for (const [fromPath] of guardOccurrences(variable)) {
        if (fromPath === statePath) return true;
    }
    for (const [fromPath] of variable.read_in_effect_occurrences ?? []) {
        if (fromPath === statePath) return true;
    }
    return false;
}

function actionStageIsAfter(readStage: string, writeStage: string): boolean {
    return (ACTION_STAGE_ORDER[readStage] ?? -1) > (ACTION_STAGE_ORDER[writeStage] ?? -1);
}

function effectWriteOccurrences(variable: VariableInfo): Array<[string, string, string | null]> {
    const effectOccurrences = variable.written_in_effect_occurrences ?? [];
    if (effectOccurrences.length > 0) {
        return effectOccurrences.map(([fromPath, toPath, occurrenceKey]) => [
            fromPath,
            toPath,
            occurrenceKey,
        ]);
    }
    return variable.written_in_effects.map(([fromPath, toPath]) => [
        fromPath,
        toPath,
        null,
    ]);
}

function variableEffectReadEdges(variable: VariableInfo): Set<string> {
    const edges = new Set<string>();
    for (const [fromPath, toPath] of variable.read_in_effect_occurrences ?? []) {
        edges.add(edgeKey(fromPath, toPath));
    }
    return edges;
}

function variableActionReadAfterWriteStages(variable: VariableInfo): Set<string> {
    const stages = new Set<string>();
    for (const [statePath, stage] of variable.read_after_write_action_stages ?? []) {
        stages.add(edgeKey(statePath, stage));
    }
    return stages;
}

function variableEffectReadAfterWriteOccurrences(variable: VariableInfo): Set<string> {
    const occurrences = new Set<string>();
    const readAfterWriteOccurrences =
        variable.read_after_write_effect_occurrences ?? [];
    for (const [fromPath, toPath, occurrenceKey] of readAfterWriteOccurrences) {
        occurrences.add(tripleKey(fromPath, toPath, occurrenceKey));
    }
    return occurrences;
}

function hasReachableReadAfterActionWrite(
    statePath: string,
    stage: string | null,
    readStates: Set<string>,
    reachabilityGraph: Record<string, string[]>,
    stateParentPaths: Record<string, string | null>,
    rootStatePath?: string,
    exitTransitionSources: Set<string> = new Set(),
    normalEdges: Record<string, Set<string>> = {},
    initialEdges: Record<string, Set<string>> = {},
    initialGuardReadEdges: Set<string> = new Set(),
    effectReadEdges: Set<string> = new Set(),
): boolean {
    if (stage !== 'exit') {
        return hasReachableRead(
            statePath,
            readStates,
            reachabilityGraph,
            normalEdges,
            initialEdges,
            initialGuardReadEdges,
        );
    }
    if (hasReachableReadAfterExitingSubtree(
        statePath,
        statePath,
        readStates,
        reachabilityGraph,
        false,
        normalEdges,
        initialEdges,
        initialGuardReadEdges,
    )) return true;
    if (hasTransitionEffectReadAfterExit(statePath, effectReadEdges)) return true;
    const exitParent = exitTransitionParentStart(
        statePath,
        stateParentPaths,
        rootStatePath,
        exitTransitionSources,
    );
    return exitParent !== null && hasReachableReadAfterExitingSubtree(
        exitParent,
        exitParent,
        readStates,
        reachabilityGraph,
        true,
        normalEdges,
        initialEdges,
        initialGuardReadEdges,
    );
}

function hasTransitionEffectReadAfterExit(statePath: string, effectReadEdges: Set<string>): boolean {
    for (const edge of effectReadEdges) {
        const [fromPath] = edge.split('\u0001', 1);
        if (fromPath === statePath || isDescendantPath(statePath, fromPath)) return true;
    }
    return false;
}

function hasReachableReadAfterExitEffect(
    fromPath: string,
    readStates: Set<string>,
    reachabilityGraph: Record<string, string[]>,
    stateParentPaths: Record<string, string | null>,
    rootStatePath?: string,
    normalEdges: Record<string, Set<string>> = {},
    initialEdges: Record<string, Set<string>> = {},
    initialGuardReadEdges: Set<string> = new Set(),
): boolean {
    const parentPath = exitTransitionParentStart(
        fromPath,
        stateParentPaths,
        rootStatePath,
        new Set([fromPath]),
    );
    return parentPath !== null && hasReachableReadAfterExitingSubtree(
        parentPath,
        parentPath,
        readStates,
        reachabilityGraph,
        true,
        normalEdges,
        initialEdges,
        initialGuardReadEdges,
    );
}

function hasReachableReadAfterExitingSubtree(
    startPath: string,
    exitedPath: string,
    readStates: Set<string>,
    reachabilityGraph: Record<string, string[]>,
    includeStart: boolean,
    normalEdges: Record<string, Set<string>>,
    initialEdges: Record<string, Set<string>>,
    initialGuardReadEdges: Set<string>,
): boolean {
    if (Object.prototype.hasOwnProperty.call(normalEdges, startPath)) {
        const seen = new Set<string>([`${startPath}\u0001false`]);
        const queue: Array<[string, boolean]> = [[startPath, false]];
        while (queue.length > 0) {
            const [current, allowInitial] = queue.shift()!;
            if (
                readStates.has(current) &&
                (allowInitial || current !== startPath || includeStart)
            ) {
                return true;
            }
            const nextPaths = new Set(normalEdges[current] ?? []);
            if (allowInitial) {
                for (const target of initialEdges[current] ?? []) {
                    if (initialGuardReadEdges.has(edgeKey(current, target))) return true;
                    nextPaths.add(target);
                }
            }
            for (const nextPath of Array.from(nextPaths).sort()) {
                const item = `${nextPath}\u0001true`;
                if (seen.has(item)) continue;
                seen.add(item);
                queue.push([nextPath, true]);
            }
        }
        return false;
    }

    if (includeStart && readStates.has(startPath)) return true;
    for (const reachable of reachabilityGraph[startPath] ?? []) {
        if (isDescendantPath(reachable, exitedPath)) continue;
        if (readStates.has(reachable)) return true;
    }
    return false;
}

function exitTransitionParentStart(
    statePath: string,
    stateParentPaths: Record<string, string | null>,
    rootStatePath: string | undefined,
    exitTransitionSources: Set<string>,
): string | null {
    if (!exitTransitionSources.has(statePath)) return null;
    const parentPath = stateParentPaths[statePath] ?? null;
    if (parentPath === null || parentPath === rootStatePath) return null;
    return parentPath;
}

function hasReachableRead(
    startPath: string,
    readStates: Set<string>,
    reachabilityGraph: Record<string, string[]>,
    normalEdges: Record<string, Set<string>>,
    initialEdges: Record<string, Set<string>>,
    initialGuardReadEdges: Set<string>,
): boolean {
    if (Object.prototype.hasOwnProperty.call(normalEdges, startPath)) {
        const seen = new Set<string>([startPath]);
        const queue = [startPath];
        while (queue.length > 0) {
            const current = queue.shift()!;
            if (readStates.has(current)) return true;
            const nextPaths = new Set(normalEdges[current] ?? []);
            for (const target of initialEdges[current] ?? []) {
                if (initialGuardReadEdges.has(edgeKey(current, target))) return true;
                nextPaths.add(target);
            }
            for (const nextPath of Array.from(nextPaths).sort()) {
                if (seen.has(nextPath)) continue;
                seen.add(nextPath);
                queue.push(nextPath);
            }
        }
        return false;
    }

    if (readStates.has(startPath)) return true;
    for (const reachable of reachabilityGraph[startPath] ?? []) {
        if (readStates.has(reachable)) return true;
    }
    return false;
}

function isDescendantPath(path: string, ancestorPath: string): boolean {
    return path.startsWith(`${ancestorPath}.`);
}
