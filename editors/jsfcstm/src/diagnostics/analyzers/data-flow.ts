import type {ModelDiagnosticJson, VariableInfo} from '../inspect';
import type {StateMachine} from '../../model/runtime';
import {collectExprVariables} from './use-def';

const INIT_MARK = '[*]';
const EXIT_MARK = '[*]';

export function collectDataFlowWarnings(
    variables: VariableInfo[],
    machine?: StateMachine,
): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const variable of variables) {
        const readStates = new Set(variable.read_in_states);
        for (const [source] of variable.read_in_guards) readStates.add(source);
        const writeStates = new Set(variable.written_in_states);
        for (const [source] of variable.written_in_effects) writeStates.add(source);
        if (!variable.affects_guard_directly && !variable.affects_guard_indirectly) {
            if (variable.abstract_actions_in_scope.length > 0) {
                out.push({
                    code: 'I_UNREFERENCED_VAR_MAYBE_ABSTRACT',
                    severity: 'info',
                    message: `Variable ${JSON.stringify(variable.name)} does not affect any transition guard, but abstract actions may use it.`,
                    span: null,
                    refs: {
                        var_name: variable.name,
                        abstract_actions_in_scope: variable.abstract_actions_in_scope,
                    },
                });
            } else {
                out.push({
                    code: 'W_UNREFERENCED_VAR',
                    severity: 'warning',
                    message: `Variable ${JSON.stringify(variable.name)} does not affect any transition guard.`,
                    span: null,
                    refs: {
                        var_name: variable.name,
                        init_value: variable.init_value,
                    },
                });
            }
            continue;
        }
        if (readStates.size > 0 && writeStates.size === 0) {
            out.push({
                code: 'W_UNWRITTEN_READ_VAR',
                severity: 'warning',
                message: `Variable ${JSON.stringify(variable.name)} is read but never written by any action or transition effect.`,
                span: null,
                refs: {
                    var_name: variable.name,
                    read_states: Array.from(readStates).sort(),
                    init_value: variable.init_value,
                },
            });
        }
        if (writeStates.size > 0 && readStates.size === 0) {
            out.push({
                code: 'W_WRITE_ONLY_VAR',
                severity: 'warning',
                message: `Variable ${JSON.stringify(variable.name)} is written but never read.`,
                span: null,
                refs: {
                    var_name: variable.name,
                    written_states: Array.from(writeStates).sort(),
                },
            });
        }
    }
    out.push(...collectGuardVarsNeverChangeDiagnostics(variables, machine));
    return out;
}

function collectGuardVarsNeverChangeDiagnostics(
    variables: VariableInfo[],
    machine?: StateMachine,
): ModelDiagnosticJson[] {
    if (!machine) return [];
    const declaredVars = new Set(variables.map(variable => variable.name));
    const writtenVars = new Set(
        variables
            .filter(variable => variable.written_in_states.length > 0 || variable.written_in_effects.length > 0)
            .map(variable => variable.name),
    );
    const out: ModelDiagnosticJson[] = [];
    for (const state of machine.allStates) {
        for (const transition of state.transitions) {
            if (!transition.guard) continue;
            const guardVars = collectExprVariables(transition.guard)
                .filter(name => declaredVars.has(name))
                .sort();
            if (guardVars.length === 0) continue;
            if (guardVars.some(name => writtenVars.has(name))) continue;
            const fromPath = transitionEndpoint(state.path, transition.fromState, true);
            const toPath = transitionEndpoint(state.path, transition.toState, false);
            out.push({
                code: 'W_GUARD_VARS_NEVER_CHANGE',
                severity: 'warning',
                message: 'Transition guard reads only variables that are never changed by actions or effects.',
                span: null,
                refs: {
                    from_path: fromPath,
                    to_path: toPath,
                    transition_span: null,
                    guard_vars: guardVars,
                },
            });
        }
    }
    return out;
}

function dottedPath(path: readonly string[]): string {
    return path.filter(item => item !== null && item !== undefined).join('.');
}

function resolveSiblingPath(parentPath: readonly string[], name: string): string {
    const parent = dottedPath(parentPath);
    return parent ? `${parent}.${name}` : name;
}

function transitionEndpoint(
    parentPath: readonly string[],
    marker: string,
    isSource: boolean,
): string {
    if (marker === 'INIT_STATE' || marker === 'EXIT_STATE') {
        return isSource ? INIT_MARK : EXIT_MARK;
    }
    return resolveSiblingPath(parentPath, marker);
}
