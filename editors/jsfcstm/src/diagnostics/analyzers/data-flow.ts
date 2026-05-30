import type {ModelDiagnosticJson, VariableInfo} from '../inspect';

export function collectDataFlowWarnings(variables: VariableInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const variable of variables) {
        const readStates = new Set(variable.read_in_states);
        for (const [source] of variable.read_in_guards) readStates.add(source);
        const writeStates = new Set(variable.written_in_states);
        for (const [source] of variable.written_in_effects) writeStates.add(source);
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
    return out;
}
