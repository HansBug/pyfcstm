import assert from 'node:assert/strict';
import {createDocument, createNode, createToken, packageModule} from './support';

// The public tree adapter also accepts token-light trees from editor recovery
// and parser integrations. These fixtures pin canonical text and fallback
// ranges without making tests depend on generated parser classes.
type Tree = packageModule.ParseTreeNode;
function expression(name: string, text: string, children: Tree[] = [], extra: object = {}): Tree {
    return createNode(name, children, {getText: () => text, ...extra});
}
const literal = (text: string) => expression('LiteralExprCondContext', text);
const number = (text: string) => expression('LiteralExprNumContext', text);
const unary = (op: string, child: Tree) => expression('UnaryExprCondContext', 'unary', [child], {op: createToken(op)});
const binary = (op: string, left: Tree, right: Tree) => expression('BinaryExprCondContext', 'binary', [left, right], {op: createToken(op)});
const conditional = (condition: Tree, yes: Tree, no: Tree) => expression('ConditionalCStyleCondNumContext', 'conditional', [condition, yes, no]);

function guardDocument(condition?: Tree) {
    const guard = createNode('Combo_guard_termContext', [], {
        getText: () => '[unfinished]', cond_expression: () => condition,
    } as any);
    const alias = createNode('Chain_combo_guard_aliasContext', [], {combo_guard_term: () => guard} as any);
    const chain = createNode('Chain_combo_triggerContext', [], {chain_combo_guard_alias: () => alias} as any);
    const trigger = createNode('Combo_transition_triggerContext', [], {chain_combo_trigger: () => chain} as any);
    const transition = createNode('NormalTransitionDefinitionContext', [], {
        from_state: createToken('A'), to_state: createToken('B'),
        combo_transition_trigger: () => trigger,
    } as any);
    const state = createNode('CompositeStateDefinitionContext', [
        createNode('State_inner_statementContext', [transition]),
    ], {state_id: {text: 'Root'}});
    return packageModule.buildAstFromTree(createNode('State_machine_dslContext', [state]),
        createDocument('state Root { A -> B : [unfinished]; }', '/tmp/adapted.fcstm'))!;
}

describe('AST context adapter compatibility', () => {
    const cases: Array<[string, Tree | undefined, string]> = [
        ['partial guard', undefined, '[unfinished]'],
        ['active atom', expression('ActiveExprCondContext', 'active("Ready")', [], {state_path: createToken('"Ready"')}), '[active("Ready")]'],
        ['literal without a wrapper child', literal('True'), '[true]'],
        ['constant without a wrapper child', expression('MathConstExprNumContext', 'pi'), '[pi]'],
        ['old condition wrapper', expression('PassExprCondContext', 'True', [literal('True')]), '[true]'],
        ['missing constructor', {constructor: undefined, getText: () => 'unknown'}, '[unknown]'],
        ['empty constructor name', {constructor: {name: ''}, getText: () => 'unknown'}, '[unknown]'],
        ['nested unary', unary('!', unary('!', literal('True'))), '[!(!true)]'],
        ['lower-priority left operand', binary('&&', binary('||', literal('True'), literal('False')), literal('True')), '[(true || false) && true]'],
        ['equal-priority right operand', binary('&&', literal('True'), binary('&&', literal('False'), literal('True'))), '[true && (false && true)]'],
        ['conditional alternatives', conditional(literal('True'), conditional(literal('False'), literal('True'), literal('False')), conditional(literal('True'), literal('False'), literal('True'))), '[(true) ? ((false) ? true : false) : ((true) ? false : true)]'],
        ['parenthesized old conditional predicate', conditional(expression('ParenExprCondContext', '(True)', [literal('True')]), literal('False'), literal('True')), '[(true) ? false : true]'],
        ['parenthesized query', expression('ParenExprCondContext', '(True)', [literal('True')]), '[(true)]'],
        ['function operand', expression('FuncExprNumContext', 'sin(1)', [number('1')], {func_name: createToken('sin')}), '[sin(1)]'],
    ];
    for (const [label, tree, expected] of cases) {
        it(`preserves ${label} through the public tree adapter`, () => {
            const ast = guardDocument(tree);
            assert.equal(ast.rootState!.transitions[0].comboTrigger!.terms[0].canonicalText, expected);
        });
    }

    it('derives region and state name ranges when token coordinates are absent', () => {
        const region = createNode('Region_definitionContext', [createNode('Region_inner_statementContext')],
            {region_id: {text: 'Motor'}} as any);
        const state = createNode('CompositeStateDefinitionContext', [createNode('State_inner_statementContext', [region])],
            {state_id: {text: 'Root'}});
        const ast = packageModule.buildAstFromTree(createNode('State_machine_dslContext', [state]),
            createDocument('state Root { region Motor {} }', '/tmp/fallback-region.fcstm'))!;
        assert.deepEqual(ast.rootState!.nameRange, {start: {line: 0, character: 6}, end: {line: 0, character: 10}});
        assert.deepEqual(ast.rootState!.regions![0].nameRange, {start: {line: 0, character: 20}, end: {line: 0, character: 25}});
        assert.deepEqual(ast.rootState!.regions![0].statements, []);
    });
});
