import type {FcstmAstOperationStatement} from '../ast';

/**
 * Keep combo provenance stable across the AST and runtime model layers.
 * pyfcstm renders assignment nodes with spaces around the assignment operator;
 * parser source text does not promise that formatting.
 */
export function canonicalComboEffectSignature(
    statements: FcstmAstOperationStatement[],
): string[] {
    return statements.map(statement => {
        if (statement.kind === 'assignmentStatement') {
            const expression = statement.expression.text.replace(/\s+/g, ' ').trim();
            return `${statement.targetName} = ${expression};`;
        }
        return statement.text.replace(/\s+/g, ' ').trim();
    });
}
