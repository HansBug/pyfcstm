import type {FcstmAstDocument, FcstmAstExpression, FcstmAstOperationStatement, FcstmAstStateDefinition, VariableRole} from './model';
import type {FcstmDiagnostic, TextRange} from '../utils/text';

/** Reject unknown serialized roles while retaining the default control declaration. */
export function requireVariableRole(role: VariableRole | undefined): VariableRole {
    const value = role ?? 'control';
    if (!['control', 'input', 'param', 'output'].includes(value)) {
        throw new RangeError(`Unknown variable role: ${JSON.stringify(value)}.`);
    }
    return value;
}

/** Validate declaration ownership before building a model or publishing editor diagnostics. */
export function collectVariableRoleDiagnostics(ast: FcstmAstDocument): FcstmDiagnostic[] {
    const diagnostics: FcstmDiagnostic[] = [];
    const readonly = new Map<string, string>();
    function emit(code: string, name: string, range: TextRange): void {
        diagnostics.push({code, severity: 'error', source: 'fcstm', range,
            message: `${code}: invalid declaration or assignment for ${JSON.stringify(name)}.`,
            data: {var_name: name}});
    }
    function hasVariable(expr: FcstmAstExpression): boolean {
        switch (expr.expressionKind) {
            case 'identifier': return true;
            case 'unary': return hasVariable(expr.operand);
            case 'binary': return hasVariable(expr.left) || hasVariable(expr.right);
            case 'function': return hasVariable(expr.argument);
            case 'parenthesized': return hasVariable(expr.expression);
            case 'conditional': return hasVariable(expr.condition) || hasVariable(expr.whenTrue) || hasVariable(expr.whenFalse);
            default: return false;
        }
    }
    for (const definition of ast.variables) {
        const role = requireVariableRole(definition.role);
        const init = definition.initializer;
        if (role === 'input') {
            readonly.set(definition.name, 'E_INPUT_WRITE');
            if (init) emit('E_INPUT_INITIALIZER', definition.name, definition.range);
        } else {
            if (role === 'param') readonly.set(definition.name, 'E_PARAM_WRITE');
            if (!init) emit('E_VARIABLE_INITIALIZER_REQUIRED', definition.name, definition.range);
            else if (hasVariable(init)) emit('E_INITIALIZER_VARIABLE_REFERENCE', definition.name, definition.range);
        }
    }
    function check(statements: FcstmAstOperationStatement[]): void {
        for (const statement of statements) {
            if (statement.kind === 'ifStatement') {
                for (const branch of statement.branches) check(branch.statements);
                if (statement.elseBlock) check(statement.elseBlock.statements);
            } else if (statement.kind === 'assignmentStatement') {
                const code = readonly.get(statement.targetName);
                if (code) emit(code, statement.targetName, statement.range);
            }
        }
    }
    function visit(state: FcstmAstStateDefinition): void {
        for (const transition of state.transitions) check(transition.postOperations);
        for (const action of [...state.enters, ...state.durings, ...state.exits, ...state.duringAspects]) {
            check(action.operationsList);
        }
        for (const child of state.substates) visit(child);
    }
    if (ast.rootState) visit(ast.rootState);
    return diagnostics;
}
