import type {ModelDiagnosticJson, VariableInfo} from '../inspect';

export function collectTypeWarnings(variables: VariableInfo[]): ModelDiagnosticJson[] {
    return [
        ...collectLiteralInitNarrowingWarnings(variables),
        ...collectLiteralAssignmentNarrowingWarnings(variables),
    ];
}

function collectLiteralInitNarrowingWarnings(variables: VariableInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const variable of variables) {
        if (variable.type !== 'int' || !isFloatLiteralText(variable.init_value)) continue;
        out.push(narrowingDiagnostic(variable.name, variable.init_value));
    }
    return out;
}

function collectLiteralAssignmentNarrowingWarnings(variables: VariableInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const variable of variables) {
        if (variable.type !== 'int') continue;
        for (const sourceExpr of variable.float_literal_assignments) {
            out.push(narrowingDiagnostic(variable.name, sourceExpr));
        }
    }
    return out;
}

function narrowingDiagnostic(varName: string, sourceExpr: string): ModelDiagnosticJson {
    return {
        code: 'W_LITERAL_TYPE_NARROWING',
        severity: 'warning',
        message: `Integer variable ${JSON.stringify(varName)} receives float literal expression ${JSON.stringify(sourceExpr)}.`,
        span: null,
        refs: {
            var_name: varName,
            target_type: 'int',
            source_expr: sourceExpr,
        },
    };
}

function isFloatLiteralText(text: string): boolean {
    const value = text.trim();
    if (value.length === 0) return false;
    const lowered = value.toLowerCase();
    if (lowered === 'pi' || lowered === 'e' || lowered === 'tau') return true;
    return (lowered.includes('.') || lowered.includes('e')) && Number.isFinite(Number(lowered));
}
