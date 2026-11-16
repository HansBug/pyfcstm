import assert from 'node:assert/strict';
import {canonicalComboEffectSignature} from '../src/model/combo-origin';
import type {FcstmAstAssignmentStatement, FcstmAstExpression} from '@pyfcstm/jsfcstm';
import {createDocument, packageModule} from './support';

async function assignment(source: string): Promise<FcstmAstAssignmentStatement> {
    const ast = await packageModule.parseAstDocument(createDocument(
        `def int value = 0; state Root { enter { value = ${source}; } }`, '/tmp/effect-text.fcstm'));
    return ast!.rootState!.enters[0].operationsList[0] as FcstmAstAssignmentStatement;
}

function binary(operator: string, left: FcstmAstExpression, right: FcstmAstExpression): FcstmAstExpression {
    return {kind: 'expression', pyNodeType: 'BinaryOp', expressionKind: 'binary', expressionType: 'num',
        text: '', range: left.range, operator, op: operator, left, expr1: left, right, expr2: right};
}

describe('canonical combo effect expressions', () => {
    for (const [source, expected] of [
        ['0x2a', '0x2a'], ['42', '42'], ['1.5', '1.5'], ['value', 'value'],
        ['pi', 'pi'], ['sin(1)', 'sin(1)'], ['(1 + 2)', '(1 + 2)'],
        ['-value', '-value'], ['value + 1', 'value + 1'],
        ['(active("/Root.Ready")) ? 1 : 0', '(active("/Root.Ready")) ? 1 : 0'],
        ['(True) ? 1 : 0', '(true) ? 1 : 0'],
    ]) {
        it(`retains canonical meaning of ${source}`, async () => {
            assert.deepEqual(canonicalComboEffectSignature([await assignment(source)]), [`value = ${expected};`]);
        });
    }

    it('preserves operator association in programmatically composed ASTs', async () => {
        const base = await assignment('1');
        const atom = base.expression;
        const cases: Array<[FcstmAstExpression, string]> = [
            [binary('*', binary('+', atom, atom), atom), '(1 + 1) * 1'],
            [binary('+', binary('*', atom, atom), atom), '1 * 1 + 1'],
            [binary('+', atom, binary('+', atom, atom)), '1 + (1 + 1)'],
            [binary('**', binary('**', atom, atom), atom), '(1 ** 1) ** 1'],
            [binary('**', binary('+', atom, atom), atom), '(1 + 1) ** 1'],
            [binary('**', atom, binary('**', atom, atom)), '1 ** 1 ** 1'],
            [binary('**', atom, binary('+', atom, atom)), '1 ** (1 + 1)'],
            [binary('+', atom, binary('*', atom, atom)), '1 + 1 * 1'],
        ];
        const unary = (await assignment('-1')).expression;
        assert.equal(unary.expressionKind, 'unary');
        if (unary.expressionKind !== 'unary') throw new Error('expected unary expression');
        cases.push([{...unary, operand: unary, expr: unary}, '-(-1)']);
        const ternary = (await assignment('(True) ? 1 : 0')).expression;
        assert.equal(ternary.expressionKind, 'conditional');
        if (ternary.expressionKind !== 'conditional') throw new Error('expected conditional');
        cases.push([{...ternary, whenTrue: ternary, whenFalse: ternary},
            '(true) ? ((true) ? 1 : 0) : ((true) ? 1 : 0)']);
        for (const [expression, expected] of cases) {
            assert.deepEqual(canonicalComboEffectSignature([{...base, expression, expr: expression}]),
                [`value = ${expected};`]);
        }
    });

    it('retains source text for a partial if branch without a condition', async () => {
        const ast = await packageModule.parseAstDocument(createDocument(
            'state Root { enter { if [True] {} } }', '/tmp/partial-if.fcstm'));
        const statement = ast!.rootState!.enters[0].operationsList[0];
        assert.equal(statement.kind, 'ifStatement');
        if (statement.kind !== 'ifStatement') throw new Error('expected if statement');
        const partial = {...statement, branches: [{...statement.branches[0], condition: null, text: 'unfinished'}]};
        assert.deepEqual(canonicalComboEffectSignature([partial]), ['if [unfinished] {\n}']);
    });
});
