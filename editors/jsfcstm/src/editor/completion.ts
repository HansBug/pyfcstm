import {getParser, type LexToken} from '../dsl/parser';
import type {
    FcstmSemanticDocument,
    FcstmSemanticTransition,
    FcstmSemanticState,
} from '../semantics';
import {getImportWorkspaceIndex} from '../workspace/imports';
import {getWorkspaceGraph} from '../workspace';
import {collectSymbolsFromTree} from './symbols';
import {
    ParseTreeNode,
    rangeContains,
    TextDocumentLike,
    TextPositionLike,
    TextRange,
} from '../utils/text';
import {rangeLength} from './ranges';

export type FcstmCompletionKind =
    | 'keyword'
    | 'constant'
    | 'function'
    | 'variable'
    | 'class'
    | 'event';

export interface FcstmCompletionItem {
    label: string;
    kind: FcstmCompletionKind;
    detail?: string;
    documentation?: string;
    insertText?: string;
    insertTextFormat?: 'plain' | 'snippet';
    sortText?: string;
}

interface FcstmContextCompletionResult {
    matched: boolean;
    items: FcstmCompletionItem[];
}

type FcstmSyntaxCompletionContext =
    | { kind: 'none' }
    | { kind: 'transitionTarget'; transition?: FcstmSemanticTransition; partial?: string }
    | { kind: 'localEvent'; transition?: FcstmSemanticTransition; sourceStateName?: string; partial?: string }
    | { kind: 'chainEvent'; transition?: FcstmSemanticTransition; partial?: string }
    | { kind: 'absoluteEventPath'; rawPath: string }
    | { kind: 'actionRef' }
    | { kind: 'pseudoStateMarker'; partial?: string }
    // Narrow follow-up contexts. Each suppresses the broad keyword dump and
    // offers only the tokens that are syntactically valid at that position.
    | { kind: 'postTransitionTarget'; partial?: string }
    | { kind: 'postTransitionTrigger' }
    | { kind: 'afterIfKeyword' }
    | { kind: 'guardBody' }
    | { kind: 'postGuardClose'; partial?: string }
    | { kind: 'postEffectKeyword' }
    | { kind: 'inEffectBody' }
    | { kind: 'aspectAfterShift'; partial?: string }
    | { kind: 'aspectAfterDuring'; partial?: string }
    | { kind: 'aspectAfterBeforeAfter'; partial?: string }
    | { kind: 'lifecycleAfterStage'; stage: 'enter' | 'during' | 'exit'; partial?: string }
    | { kind: 'lifecycleAfterAbstract' }
    | { kind: 'identifierSlot' }
    | { kind: 'variableDefinitionRhs' }
    | { kind: 'defTypeKeyword' }
    | { kind: 'postPseudoKeyword' }
    | { kind: 'postForcedSource' };

type FcstmImportCompletionContext =
    | { kind: 'none' }
    | { kind: 'importAliasKeyword' }
    | { kind: 'importNamedKeyword' }
    | { kind: 'importBlock' };

export const KEYWORDS = [
    'state', 'pseudo', 'named', 'def', 'event', 'import', 'as',
    'enter', 'during', 'exit', 'before', 'after',
    'abstract', 'ref', 'effect', 'if', 'else',
    'int', 'float',
    'and', 'or', 'not'
];

export const MATH_CONSTANTS = [
    {name: 'pi', detail: 'π ≈ 3.14159', documentation: 'The mathematical constant π (pi)'},
    {name: 'E', detail: 'e ≈ 2.71828', documentation: 'The mathematical constant e (Euler\'s number)'},
    {name: 'tau', detail: 'τ ≈ 6.28318', documentation: 'The mathematical constant τ (tau), equal to 2π'},
    {name: 'true', detail: 'boolean', documentation: 'Boolean true value'},
    {name: 'false', detail: 'boolean', documentation: 'Boolean false value'},
    {name: 'True', detail: 'boolean', documentation: 'Boolean true value (Python-style)'},
    {name: 'False', detail: 'boolean', documentation: 'Boolean false value (Python-style)'}
];

export const MATH_FUNCTIONS = [
    {name: 'sin', params: '(x)', doc: 'Sine function'},
    {name: 'cos', params: '(x)', doc: 'Cosine function'},
    {name: 'tan', params: '(x)', doc: 'Tangent function'},
    {name: 'asin', params: '(x)', doc: 'Arcsine function'},
    {name: 'acos', params: '(x)', doc: 'Arccosine function'},
    {name: 'atan', params: '(x)', doc: 'Arctangent function'},
    {name: 'sinh', params: '(x)', doc: 'Hyperbolic sine function'},
    {name: 'cosh', params: '(x)', doc: 'Hyperbolic cosine function'},
    {name: 'tanh', params: '(x)', doc: 'Hyperbolic tangent function'},
    {name: 'asinh', params: '(x)', doc: 'Inverse hyperbolic sine function'},
    {name: 'acosh', params: '(x)', doc: 'Inverse hyperbolic cosine function'},
    {name: 'atanh', params: '(x)', doc: 'Inverse hyperbolic tangent function'},
    {name: 'sqrt', params: '(x)', doc: 'Square root function'},
    {name: 'cbrt', params: '(x)', doc: 'Cube root function'},
    {name: 'exp', params: '(x)', doc: 'Exponential function (e^x)'},
    {name: 'log', params: '(x)', doc: 'Natural logarithm (base e)'},
    {name: 'log10', params: '(x)', doc: 'Base-10 logarithm'},
    {name: 'log2', params: '(x)', doc: 'Base-2 logarithm'},
    {name: 'log1p', params: '(x)', doc: 'Natural logarithm of (1 + x)'},
    {name: 'abs', params: '(x)', doc: 'Absolute value'},
    {name: 'ceil', params: '(x)', doc: 'Ceiling function (round up)'},
    {name: 'floor', params: '(x)', doc: 'Floor function (round down)'},
    {name: 'round', params: '(x)', doc: 'Round to nearest integer'},
    {name: 'trunc', params: '(x)', doc: 'Truncate to integer'},
    {name: 'sign', params: '(x)', doc: 'Sign function (-1, 0, or 1)'}
];

export function isInComment(text: string): boolean {
    if (text.includes('//')) {
        return true;
    }
    if (text.includes('#')) {
        return true;
    }
    const openCount = (text.match(/\/\*/g) || []).length;
    const closeCount = (text.match(/\*\//g) || []).length;
    return openCount > closeCount;
}

export function isInString(text: string): boolean {
    let inDoubleQuote = false;
    let inSingleQuote = false;

    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        const prevChar = i > 0 ? text[i - 1] : '';

        if (char === '"' && prevChar !== '\\') {
            inDoubleQuote = !inDoubleQuote;
        } else if (char === '\'' && prevChar !== '\\') {
            inSingleQuote = !inSingleQuote;
        }
    }

    return inDoubleQuote || inSingleQuote;
}

function getConstantCompletions(): FcstmCompletionItem[] {
    return MATH_CONSTANTS.map(constant => ({
        label: constant.name,
        kind: 'constant',
        detail: constant.detail,
        documentation: constant.documentation,
        sortText: `1_${constant.name}`,
    }));
}

function getFunctionCompletions(): FcstmCompletionItem[] {
    return MATH_FUNCTIONS.map(func => ({
        label: func.name,
        kind: 'function',
        detail: func.params,
        documentation: func.doc,
        insertText: `${func.name}($1)$0`,
        insertTextFormat: 'snippet',
        sortText: `2_${func.name}`,
    }));
}

async function getDocumentSymbolCompletions(document: TextDocumentLike): Promise<FcstmCompletionItem[]> {
    const items: FcstmCompletionItem[] = [];
    const tree = await getParser().parseTree(document.getText());
    if (!tree) {
        return items;
    }

    const fallbackSymbols = collectSymbolsFromTree(tree as ParseTreeNode);
    for (const variable of fallbackSymbols.variables) {
        items.push({
            label: variable,
            kind: 'variable',
            sortText: `3_${variable}`,
        });
    }
    for (const state of fallbackSymbols.states) {
        items.push({
            label: state,
            kind: 'class',
            sortText: `4_${state}`,
        });
    }
    for (const event of fallbackSymbols.events) {
        if (!isValidIdentifierSegment(event)) {
            continue;
        }
        items.push({
            label: event,
            kind: 'event',
            sortText: `5_${event}`,
        });
    }

    return items;
}

function findInnermostState(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSemanticState | undefined {
    return semantic.states
        .filter(state => rangeContains(state.range, position))
        .sort((left, right) => rangeLength(left.range) - rangeLength(right.range))
        [0];
}

function collectLookupStates(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSemanticState[] {
    const statesById = new Map(semantic.states.map(item => [item.identity.id, item]));
    const currentState = findInnermostState(semantic, position);
    const states: FcstmSemanticState[] = [];

    let cursor = currentState;
    while (cursor) {
        states.push(cursor);
        cursor = cursor.parentStateId ? statesById.get(cursor.parentStateId) : undefined;
    }

    if (states.length === 0 && semantic.machine.rootStateId) {
        const rootState = statesById.get(semantic.machine.rootStateId);
        if (rootState) {
            states.push(rootState);
        }
    }

    return states;
}

function getCurrentScopeState(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSemanticState | undefined {
    const currentState = findInnermostState(semantic, position);
    if (currentState) {
        return currentState;
    }

    return semantic.machine.rootStateId
        ? semantic.states.find(item => item.identity.id === semantic.machine.rootStateId)
        : undefined;
}

function findRootState(semantic: FcstmSemanticDocument): FcstmSemanticState | undefined {
    return semantic.machine.rootStateId
        ? semantic.states.find(item => item.identity.id === semantic.machine.rootStateId)
        : semantic.states.find(item => !item.parentStateId);
}

function matchesPartial(candidate: string, partial: string): boolean {
    return !partial || candidate.toLowerCase().startsWith(partial.toLowerCase());
}

function isValidIdentifierSegment(text: string): boolean {
    return /^[A-Za-z_][A-Za-z0-9_]*$/.test(text);
}

function comparePositions(left: TextPositionLike, right: TextPositionLike): number {
    if (left.line !== right.line) {
        return left.line - right.line;
    }

    return left.character - right.character;
}

function findSemanticTransitionAtPosition(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmSemanticTransition | undefined {
    return semantic.transitions
        .filter(item => rangeContains(item.range, position))
        .sort((left, right) => rangeLength(left.range) - rangeLength(right.range))
        [0];
}

function findStateById(
    semantic: FcstmSemanticDocument,
    stateId?: string
): FcstmSemanticState | undefined {
    if (!stateId) {
        return undefined;
    }

    return semantic.states.find(item => item.identity.id === stateId);
}

function isQuotedToken(token: LexToken | undefined): boolean {
    const text = token?.text || '';
    return (text.startsWith('"') && text.endsWith('"')) || (text.startsWith('\'') && text.endsWith('\''));
}

function extractImportCompletionContextFromLineTokens(tokens: LexToken[]): FcstmImportCompletionContext {
    if ((tokens[0]?.text || '') !== 'import') {
        return {kind: 'none'};
    }

    if (tokens.length >= 2 && isQuotedToken(tokens[1]) && !tokens.some(token => token.text === 'as')) {
        return {kind: 'importAliasKeyword'};
    }

    const asIndex = tokens.findIndex(token => token.text === 'as');
    if (asIndex >= 0) {
        const aliasToken = tokens[asIndex + 1];
        const namedIndex = tokens.findIndex(token => token.text === 'named');
        const braceIndex = tokens.findIndex(token => token.text === '{');
        if (aliasToken && namedIndex < 0 && braceIndex < 0) {
            return {kind: 'importNamedKeyword'};
        }
    }

    if (tokens.some(token => token.text === '{')) {
        return {kind: 'importBlock'};
    }

    return {kind: 'none'};
}

function hasTrailingSpace(beforeCursor: string): boolean {
    return /[ \t]$/.test(beforeCursor);
}

function extractSyntaxCompletionContextFromLineTokens(
    tokens: LexToken[],
    semantic: FcstmSemanticDocument | undefined,
    position: TextPositionLike,
    beforeCursor: string
): FcstmSyntaxCompletionContext {
    const trailing = hasTrailingSpace(beforeCursor);

    if (tokens.length === 1 && tokens[0]?.text === '[') {
        return {kind: 'pseudoStateMarker', partial: '['};
    }

    // Detect "cursor is inside an unclosed `{` on this line whose opening
    // was preceded by an operation-block keyword". This handles forms like
    //   state A { enter { │ }
    // where the block opener is not the first token on the line.
    const OPERATION_BLOCK_OPENERS = new Set(['enter', 'during', 'exit', 'effect']);
    let openIndex = -1;
    let depth = 0;
    for (let i = tokens.length - 1; i >= 0; i--) {
        if (tokens[i].text === '}') {
            depth++;
        } else if (tokens[i].text === '{') {
            if (depth === 0) {
                openIndex = i;
                break;
            }
            depth--;
        }
    }
    if (openIndex >= 0) {
        // Scan backwards from the `{` until we hit either the opener keyword
        // or something that isn't part of an action/effect prefix.
        for (let j = openIndex - 1; j >= 0; j--) {
            const text = tokens[j].text;
            if (OPERATION_BLOCK_OPENERS.has(text)) {
                return {kind: 'inEffectBody'};
            }
            // Traverse identifier / `abstract` / `ref` / `>>` / `during`
            // / `before` / `after` prefixes — these can legitimately sit
            // between the opener and the `{`.
            if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(text)
                && text !== '>>'
                && text !== 'before'
                && text !== 'after') {
                break;
            }
        }
    }

    const firstText = tokens[0]?.text;

    // Aspect chain: `>> [during [before|after [abstract] [IDENT]]]`.
    if (firstText === '>>') {
        const rest = tokens.slice(1);
        const restTexts = rest.map(token => token.text);
        if (rest.length === 0) {
            return trailing ? {kind: 'aspectAfterShift', partial: ''} : {kind: 'none'};
        }
        if (rest.length === 1 && !trailing) {
            return {kind: 'aspectAfterShift', partial: restTexts[0]};
        }
        if (rest[0].text === 'during') {
            if (rest.length === 1) {
                return {kind: 'aspectAfterDuring', partial: ''};
            }
            if (rest.length === 2 && !trailing) {
                return {kind: 'aspectAfterDuring', partial: restTexts[1]};
            }
            if (rest[1].text === 'before' || rest[1].text === 'after') {
                if (rest.length === 2) {
                    return {kind: 'aspectAfterBeforeAfter', partial: ''};
                }
                if (rest.length === 3 && !trailing) {
                    return {kind: 'aspectAfterBeforeAfter', partial: restTexts[2]};
                }
                if (rest[2].text === 'abstract') {
                    return {kind: 'identifierSlot'};
                }
                if (rest[2].text === '{') {
                    return {kind: 'none'};
                }
            }
        }
        return {kind: 'none'};
    }

    // Lifecycle modifier at a state body: `enter [abstract|ref|IDENT] …`.
    if (firstText === 'enter' || firstText === 'during' || firstText === 'exit') {
        const rest = tokens.slice(1);
        const stage = firstText as 'enter' | 'during' | 'exit';
        if (rest.length === 0) {
            return trailing
                ? {kind: 'lifecycleAfterStage', stage, partial: ''}
                : {kind: 'none'};
        }
        const afterFirst = rest[0].text;
        if (afterFirst === '{') {
            // Operation-block body opened on this line. Parser can't produce
            // a block range until `}` is written, so detect it from tokens.
            return {kind: 'inEffectBody'};
        }
        if (afterFirst === 'before' || afterFirst === 'after') {
            if (stage !== 'during') {
                return {kind: 'none'};
            }
            if (rest.length === 1 && !trailing) {
                return {kind: 'lifecycleAfterStage', stage, partial: afterFirst};
            }
            if (rest.length >= 1 && trailing) {
                return {kind: 'lifecycleAfterStage', stage, partial: ''};
            }
            return {kind: 'none'};
        }
        if (afterFirst === 'abstract') {
            if (rest.length === 1) {
                return {kind: 'lifecycleAfterAbstract'};
            }
            return {kind: 'identifierSlot'};
        }
        if (afterFirst === 'ref') {
            return {kind: 'actionRef'};
        }
        if (isValidIdentifierSegment(afterFirst)) {
            return {kind: 'identifierSlot'};
        }
        return {kind: 'none'};
    }

    // Variable definition: `def [int|float] IDENT = EXPR;`
    if (firstText === 'def') {
        const tokenTexts = tokens.map(token => token.text);
        const eqIndex = tokenTexts.indexOf('=');
        if (eqIndex >= 0) {
            return {kind: 'variableDefinitionRhs'};
        }
        if (tokens.length === 1 && trailing) {
            return {kind: 'defTypeKeyword'};
        }
        if (tokens.length === 2 && !trailing
            && (tokenTexts[1] === 'int' || tokenTexts[1] === 'float'
                || 'int'.startsWith(tokenTexts[1]) || 'float'.startsWith(tokenTexts[1]))) {
            return {kind: 'defTypeKeyword'};
        }
        return {kind: 'identifierSlot'};
    }

    // Direct naming keywords where the next token is a new identifier.
    if (firstText === 'state' || firstText === 'event') {
        const arrowHere = tokens.some(token => token.text === '->');
        if (!arrowHere) {
            const rest = tokens.slice(1);
            if (rest.length === 0 && trailing) {
                return {kind: 'identifierSlot'};
            }
            if (rest.length === 1 && !trailing) {
                return {kind: 'identifierSlot'};
            }
        }
    }

    if (firstText === 'pseudo') {
        if (tokens[1]?.text === 'state') {
            const rest = tokens.slice(2);
            if (rest.length === 0 && trailing) {
                return {kind: 'identifierSlot'};
            }
            if (rest.length === 1 && !trailing) {
                return {kind: 'identifierSlot'};
            }
        } else if (tokens.length === 1 && trailing) {
            // `pseudo │` — only `state` can follow.
            return {kind: 'postPseudoKeyword'};
        }
    }

    // `!State │` / `!* │` — forced transition source written, expect `->`.
    if (firstText === '!') {
        const hasArrow = tokens.some(t => t.text === '->');
        if (!hasArrow) {
            if (tokens.length >= 2 && trailing) {
                return {kind: 'postForcedSource'};
            }
        }
        // The arrow path below will naturally pick up `!Foo -> B` once the
        // arrow token is present.
    }

    // `X named │` — about to type an opening quote; suppress the dump.
    const namedIdx = tokens.findIndex(token => token.text === 'named');
    if (namedIdx >= 0 && !tokens.some(token => token.text === '->') && namedIdx === tokens.length - 1 && trailing) {
        return {kind: 'identifierSlot'};
    }

    // Action-ref fallback for partial parses.
    const refIndex = tokens.findIndex(token => token.text === 'ref');
    if (refIndex >= 0) {
        return {kind: 'actionRef'};
    }

    // Transition line: source `->` target [[:|::] trigger] [if [...]] [effect {...}];
    const arrowIndex = tokens.findIndex(token => token.text === '->');
    if (arrowIndex < 0) {
        return {kind: 'none'};
    }

    const transition = semantic ? findSemanticTransitionAtPosition(semantic, position) : undefined;
    const afterArrow = tokens.slice(arrowIndex + 1);
    const sourceStateName = tokens[arrowIndex - 1]?.text;
    if (afterArrow.length === 0) {
        return {kind: 'transitionTarget', transition, partial: ''};
    }

    const targetToken = afterArrow[0];
    const operatorToken = afterArrow[1];
    if (!targetToken) {
        return {kind: 'transitionTarget', transition, partial: ''};
    }

    if (!operatorToken) {
        if (trailing) {
            // `A -> B │` — target finished, choosing next syntactic slot.
            return {kind: 'postTransitionTarget'};
        }
        return {kind: 'transitionTarget', transition, partial: targetToken.text};
    }

    if (operatorToken.text === '::') {
        const afterOp = afterArrow.slice(2);
        const partial = afterOp.map(token => token.text).join('');
        if (partial.startsWith('/')) {
            // `::/…` is invalid scope syntax — suppress the dump entirely.
            return {kind: 'identifierSlot'};
        }
        // `:: Event │` (trailing space after a completed event identifier)
        // — user has finished the trigger and is deciding what comes next.
        // The grammar allows an optional `effect { … }` block here.
        if (afterOp.length === 1 && trailing && isValidIdentifierSegment(afterOp[0].text)) {
            return {kind: 'postTransitionTrigger'};
        }
        // `:: Event effect │` / `:: Event effect {` handling.
        if (afterOp.length >= 2 && afterOp[1].text === 'effect') {
            if (afterOp.length === 2 && trailing) {
                return {kind: 'postEffectKeyword'};
            }
            if (afterOp.some(t => t.text === '{')) {
                return {kind: 'inEffectBody'};
            }
        }
        return {kind: 'localEvent', transition, sourceStateName, partial};
    }

    if (operatorToken.text === ':') {
        const afterColon = afterArrow.slice(2);
        const rawPath = afterColon.map(token => token.text).join('');
        if (rawPath.startsWith('/')) {
            return {kind: 'absoluteEventPath', rawPath};
        }

        if (rawPath === 'if' && !trailing) {
            // Still typing the keyword — let chainEvent fallback surface it.
            return {kind: 'chainEvent', transition, partial: rawPath};
        }

        // `: Event │` (trailing space after a completed event identifier,
        // not followed by `if`/`effect` yet) — user finished the chain-event
        // trigger and can continue with an optional `effect { … }` block.
        if (afterColon.length === 1
            && trailing
            && afterColon[0].text !== 'if'
            && isValidIdentifierSegment(afterColon[0].text)) {
            return {kind: 'postTransitionTrigger'};
        }

        // `: Event effect …` handling mirrors the `::` path above.
        if (afterColon.length >= 2
            && afterColon[1].text === 'effect'
            && isValidIdentifierSegment(afterColon[0].text)) {
            if (afterColon.length === 2 && trailing) {
                return {kind: 'postEffectKeyword'};
            }
            if (afterColon.some(t => t.text === '{')) {
                return {kind: 'inEffectBody'};
            }
        }

        if (afterColon[0]?.text === 'if') {
            const openIdx = afterColon.findIndex(t => t.text === '[');
            const closeIdx = afterColon.findIndex(t => t.text === ']');

            if (afterColon.length === 1 && trailing) {
                return {kind: 'afterIfKeyword'};
            }
            if (openIdx < 0 && trailing) {
                return {kind: 'identifierSlot'};
            }
            if (openIdx >= 0 && closeIdx < 0) {
                return {kind: 'guardBody'};
            }
            if (closeIdx >= 0) {
                const afterClose = afterColon.slice(closeIdx + 1);
                if (afterClose.length === 0) {
                    return {kind: 'postGuardClose', partial: ''};
                }
                const effectTok = afterClose[0];
                const openBraceIdx = afterClose.findIndex(t => t.text === '{');
                if (openBraceIdx >= 0) {
                    return {kind: 'inEffectBody'};
                }
                if (effectTok.text === 'effect') {
                    if (afterClose.length === 1 && !trailing) {
                        return {kind: 'postGuardClose', partial: effectTok.text};
                    }
                    if (afterClose.length === 1 && trailing) {
                        return {kind: 'postEffectKeyword'};
                    }
                }
                if (afterClose.length === 1 && !trailing && isValidIdentifierSegment(effectTok.text)) {
                    return {kind: 'postGuardClose', partial: effectTok.text};
                }
            }
            return {kind: 'identifierSlot'};
        }

        return {kind: 'chainEvent', transition, partial: rawPath};
    }

    // `A -> B effect { ... }` path (no guard, no trigger).
    if (operatorToken.text === 'effect') {
        const afterEffect = afterArrow.slice(2);
        if (afterEffect.length === 0 && trailing) {
            return {kind: 'postEffectKeyword'};
        }
        if (afterEffect.some(t => t.text === '{')) {
            return {kind: 'inEffectBody'};
        }
        return {kind: 'none'};
    }

    // `A -> B if [...]` path (no trigger before the guard).
    if (operatorToken.text === 'if') {
        const afterIf = afterArrow.slice(2);
        if (afterIf.length === 0 && trailing) {
            return {kind: 'afterIfKeyword'};
        }
        const openIdx = afterIf.findIndex(t => t.text === '[');
        const closeIdx = afterIf.findIndex(t => t.text === ']');
        if (openIdx >= 0 && closeIdx < 0) {
            return {kind: 'guardBody'};
        }
        if (closeIdx >= 0) {
            const afterClose = afterIf.slice(closeIdx + 1);
            if (afterClose.length === 0) {
                return {kind: 'postGuardClose', partial: ''};
            }
            if (afterClose.some(t => t.text === '{')) {
                return {kind: 'inEffectBody'};
            }
            if (afterClose[0].text === 'effect') {
                if (afterClose.length === 1 && trailing) {
                    return {kind: 'postEffectKeyword'};
                }
                if (afterClose.length === 1 && !trailing) {
                    return {kind: 'postGuardClose', partial: afterClose[0].text};
                }
            }
            if (afterClose.length === 1 && !trailing && isValidIdentifierSegment(afterClose[0].text)) {
                return {kind: 'postGuardClose', partial: afterClose[0].text};
            }
        }
        return {kind: 'none'};
    }

    return {kind: 'transitionTarget', transition};
}

function findTransitionOperatorToken(
    tokens: LexToken[],
    operatorText: ':' | '::'
): LexToken | undefined {
    const arrowIndex = tokens.findIndex(token => token.text === '->');
    if (arrowIndex < 0) {
        return undefined;
    }

    return tokens.slice(arrowIndex + 1).find(token => token.text === operatorText);
}

function getTriggerInsertTextPrefix(
    beforeCursor: string,
    operatorToken: LexToken | undefined
): string {
    if (!operatorToken) {
        return '';
    }

    const operatorEnd = operatorToken.column + operatorToken.text.length;
    const afterOperatorText = beforeCursor.slice(operatorEnd);
    if (afterOperatorText.startsWith(' ') || afterOperatorText.startsWith('\t')) {
        return '';
    }

    return ' ';
}

function makePseudoStateCompletionItem(): FcstmCompletionItem {
    return {
        label: '[*]',
        kind: 'keyword',
        detail: 'Pseudo-state marker',
        insertText: '[*]',
        sortText: '0_init_marker',
    };
}

function pushPseudoStateMarker(
    items: FcstmCompletionItem[],
    partial = ''
): void {
    if (!matchesPartial('[*]', partial)) {
        return;
    }

    items.push(makePseudoStateCompletionItem());
}

function pushChildStateNames(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    items: FcstmCompletionItem[],
    options: {
        includeSelf?: boolean;
        pathPrefix?: string;
        insertTextPrefix?: string;
        partial?: string;
        detailPrefix?: string;
        sortPrefix?: string;
    } = {}
): void {
    if (!scopeState) {
        return;
    }

    const {
        includeSelf = false,
        pathPrefix = '',
        insertTextPrefix = pathPrefix,
        partial = '',
        detailPrefix,
        sortPrefix = '4_state',
    } = options;
    const seen = new Set<string>();

    if (includeSelf && !seen.has(scopeState.name) && matchesPartial(scopeState.name, partial)) {
        seen.add(scopeState.name);
        items.push({
            label: `${pathPrefix}${scopeState.name}`,
            kind: 'class',
            detail: detailPrefix || scopeState.identity.path.join('.'),
            insertText: `${insertTextPrefix}${scopeState.name}`,
            sortText: `${sortPrefix}_${scopeState.name}`,
        });
    }

    for (const candidate of semantic.states.filter(item => item.parentStateId === scopeState.identity.id)) {
        if (seen.has(candidate.name) || !matchesPartial(candidate.name, partial)) {
            continue;
        }

        seen.add(candidate.name);
        items.push({
            label: `${pathPrefix}${candidate.name}`,
            kind: 'class',
            detail: detailPrefix || candidate.identity.path.join('.'),
            insertText: `${insertTextPrefix}${candidate.name}`,
            sortText: `${sortPrefix}_${candidate.name}`,
        });
    }
}

function pushVisibleImportAliases(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    items: FcstmCompletionItem[]
): void {
    if (!scopeState) {
        return;
    }

    const seen = new Set<string>();

    for (const importItem of semantic.imports.filter(item => item.ownerStateId === scopeState.identity.id)) {
        if (seen.has(importItem.alias)) {
            continue;
        }

        seen.add(importItem.alias);
        items.push({
            label: importItem.alias,
            kind: 'class',
            detail: 'Imported state alias',
            sortText: `4_import_${importItem.alias}`,
        });
    }
}

function pushDeclaredEventsForState(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    items: FcstmCompletionItem[],
    options: {
        pathPrefix?: string;
        insertTextPrefix?: string;
        partial?: string;
        detailPrefix?: string;
        sortPrefix?: string;
        declaredOnly?: boolean;
    } = {}
): void {
    if (!scopeState) {
        return;
    }

    const {
        pathPrefix = '',
        insertTextPrefix = pathPrefix,
        partial = '',
        detailPrefix,
        sortPrefix = '5_event',
        declaredOnly = true,
    } = options;
    const seen = new Set<string>();

    for (const event of semantic.events.filter(item => (
        (!declaredOnly || item.declared)
        && item.statePath.join('.') === scopeState.identity.path.join('.')
    ))) {
        if (
            seen.has(event.name)
            || !isValidIdentifierSegment(event.name)
            || !matchesPartial(event.name, partial)
        ) {
            continue;
        }

        seen.add(event.name);
        items.push({
            label: `${pathPrefix}${event.name}`,
            kind: 'event',
            detail: detailPrefix || event.identity.qualifiedName,
            insertText: `${insertTextPrefix}${event.name}`,
            sortText: `${sortPrefix}_${event.name}`,
        });
    }
}

function pushVisibleNamedActions(
    semantic: FcstmSemanticDocument,
    lookupStates: FcstmSemanticState[],
    items: FcstmCompletionItem[]
): void {
    const seen = new Set<string>();
    for (const scopeState of lookupStates) {
        for (const action of semantic.actions.filter(item => item.ownerStateId === scopeState.identity.id && item.name)) {
            if (!action.name || seen.has(action.identity.qualifiedName)) {
                continue;
            }

            seen.add(action.identity.qualifiedName);
            items.push({
                label: action.identity.qualifiedName,
                kind: 'function',
                detail: 'Named lifecycle action',
                insertText: action.identity.qualifiedName,
                sortText: `2_ref_${action.identity.qualifiedName}`,
            });
        }
    }
}

function findStateOwningRangeStart(
    semantic: FcstmSemanticDocument,
    range: TextRange | undefined
): FcstmSemanticState | undefined {
    if (!range) {
        return undefined;
    }

    return semantic.states
        .filter(state => rangeContains(state.range, range.start))
        .sort((left, right) => rangeLength(left.range) - rangeLength(right.range))
        [0];
}

function hasPathMatch(candidates: string[][], expectedPath: string[]): boolean {
    const expectedKey = expectedPath.join('.');
    return candidates.some(path => path.join('.') === expectedKey);
}

function collectDerivedEventContainerPaths(
    semantic: FcstmSemanticDocument,
    event: FcstmSemanticDocument['events'][number],
    position?: TextPositionLike
): {
    declarationPath?: string[];
    localPaths: string[][];
    chainPaths: string[][];
    absolutePaths: string[][];
} {
    const localPathMap = new Map<string, string[]>();
    const chainPathMap = new Map<string, string[]>();
    const absolutePathMap = new Map<string, string[]>();
    const declarationPath = findStateOwningRangeStart(semantic, event.declarationAst?.range)?.identity.path;

    for (const transition of semantic.transitions) {
        if (!transition.trigger || transition.trigger.eventId !== event.identity.id) {
            continue;
        }
        if (position && comparePositions(transition.trigger.range.start, position) > 0) {
            continue;
        }

        if (transition.trigger.scope === 'local' && transition.sourceStatePath) {
            localPathMap.set(transition.sourceStatePath.join('.'), transition.sourceStatePath);
        } else if (transition.trigger.scope === 'chain') {
            chainPathMap.set(transition.ownerStatePath.join('.'), transition.ownerStatePath);
        } else if (transition.trigger.scope === 'absolute') {
            const containerPath = transition.trigger.normalizedPath.slice(0, -1);
            absolutePathMap.set(containerPath.join('.'), containerPath);
        }
    }

    return {
        declarationPath,
        localPaths: [...localPathMap.values()],
        chainPaths: [...chainPathMap.values()],
        absolutePaths: [...absolutePathMap.values()],
    };
}

function eventMatchesScopeState(
    semantic: FcstmSemanticDocument,
    event: FcstmSemanticDocument['events'][number],
    scopeState: FcstmSemanticState,
    scope: 'local' | 'chain' | 'absolute',
    position?: TextPositionLike
): boolean {
    const {declarationPath, localPaths, chainPaths, absolutePaths} = collectDerivedEventContainerPaths(
        semantic,
        event,
        position
    );

    if (declarationPath && declarationPath.join('.') === scopeState.identity.path.join('.')) {
        return true;
    }

    if (scope === 'local') {
        return hasPathMatch(localPaths, scopeState.identity.path);
    }
    if (scope === 'chain') {
        const rootState = findRootState(semantic);
        const isRootScope = Boolean(rootState && rootState.identity.path.join('.') === scopeState.identity.path.join('.'));
        return hasPathMatch(chainPaths, scopeState.identity.path)
            || (isRootScope && hasPathMatch(absolutePaths, scopeState.identity.path));
    }
    return hasPathMatch(absolutePaths, scopeState.identity.path);
}

function pushVisibleScopedEvents(
    semantic: FcstmSemanticDocument,
    scopeState: FcstmSemanticState | undefined,
    scope: 'local' | 'chain' | 'absolute',
    items: FcstmCompletionItem[],
    options: {
        position?: TextPositionLike;
        pathPrefix?: string;
        insertTextPrefix?: string;
        partial?: string;
        detailPrefix?: string;
        sortPrefix?: string;
    } = {}
): void {
    if (!scopeState) {
        return;
    }

    const {
        pathPrefix = '',
        insertTextPrefix = pathPrefix,
        position,
        partial = '',
        detailPrefix,
        sortPrefix = '5_event',
    } = options;
    const seen = new Set<string>();

    for (const event of semantic.events) {
        if (
            seen.has(event.name)
            || !isValidIdentifierSegment(event.name)
            || !matchesPartial(event.name, partial)
            || !eventMatchesScopeState(semantic, event, scopeState, scope, position)
        ) {
            continue;
        }

        seen.add(event.name);
        items.push({
            label: `${pathPrefix}${event.name}`,
            kind: 'event',
            detail: detailPrefix || event.identity.qualifiedName,
            insertText: `${insertTextPrefix}${event.name}`,
            sortText: `${sortPrefix}_${event.name}`,
        });
    }
}

function resolveVisibleStateReference(
    semantic: FcstmSemanticDocument,
    lookupStates: FcstmSemanticState[],
    stateName?: string
): FcstmSemanticState | undefined {
    if (!stateName) {
        return undefined;
    }

    const rootState = semantic.machine.rootStateId
        ? semantic.states.find(item => item.identity.id === semantic.machine.rootStateId)
        : undefined;
    if (rootState?.name === stateName) {
        return rootState;
    }

    for (const scopeState of lookupStates) {
        const candidate = semantic.states.find(item => (
            item.parentStateId === scopeState.identity.id
            && item.name === stateName
        ));
        if (candidate) {
            return candidate;
        }
    }

    const uniqueGlobalMatches = semantic.states.filter(item => item.name === stateName);
    return uniqueGlobalMatches.length === 1 ? uniqueGlobalMatches[0] : undefined;
}

function collectScopedSymbolCompletions(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    const seen = new Set<string>();
    const lookupStates = collectLookupStates(semantic, position);
    const currentScope = getCurrentScopeState(semantic, position);

    for (const variable of semantic.variables) {
        pushUniqueCompletion(items, seen, {
            label: variable.name,
            kind: 'variable',
            sortText: `3_${variable.name}`,
        });
    }

    for (const candidate of collectStateAndImportCompletions(semantic, currentScope)) {
        pushUniqueCompletion(items, seen, candidate);
    }

    for (const candidate of collectEventCompletions(semantic, lookupStates)) {
        pushUniqueCompletion(items, seen, candidate);
    }

    for (const candidate of collectNamedActionCompletions(semantic, lookupStates)) {
        pushUniqueCompletion(items, seen, candidate);
    }

    return items;
}

function collectStateAndImportCompletions(
    semantic: FcstmSemanticDocument,
    currentScope: FcstmSemanticState | undefined
): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    pushChildStateNames(semantic, currentScope, items, {
        sortPrefix: '4_scoped_state',
    });
    pushVisibleImportAliases(semantic, currentScope, items);
    return items;
}

function collectEventCompletions(
    semantic: FcstmSemanticDocument,
    lookupStates: FcstmSemanticState[]
): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    for (const scopeState of lookupStates) {
        pushDeclaredEventsForState(semantic, scopeState, items, {
            sortPrefix: '5_scoped_event',
        });
    }
    return items;
}

function collectNamedActionCompletions(
    semantic: FcstmSemanticDocument,
    lookupStates: FcstmSemanticState[]
): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    pushVisibleNamedActions(semantic, lookupStates, items);
    return items;
}

async function getActiveImportEntry(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<{ sourcePath: string } | null> {
    const parsed = await getImportWorkspaceIndex().parseDocument(document);
    const entry = parsed.imports.find(item => rangeContains(item.statementRange, position));
    return entry ? {sourcePath: entry.sourcePath} : null;
}

async function getImportAwareCompletions(
    document: TextDocumentLike,
    position: TextPositionLike,
    lineTokens: LexToken[]
): Promise<FcstmContextCompletionResult> {
    const items: FcstmCompletionItem[] = [];
    const syntaxContext = extractImportCompletionContextFromLineTokens(lineTokens);
    let matched = syntaxContext.kind !== 'none';

    if (syntaxContext.kind === 'importAliasKeyword') {
        items.push({
            label: 'as',
            kind: 'keyword',
            sortText: '0_as',
        });
    }

    if (syntaxContext.kind === 'importNamedKeyword') {
        items.push({
            label: 'named',
            kind: 'keyword',
            sortText: '0_named',
        });
    }

    if (syntaxContext.kind === 'importBlock') {
        items.push({
            label: 'def',
            kind: 'keyword',
            sortText: '0_def_import',
        });
        items.push({
            label: 'event',
            kind: 'keyword',
            sortText: '0_event_import',
        });
    }

    const activeImport = await getActiveImportEntry(document, position);
    if (!activeImport) {
        return {matched, items};
    }

    matched = true;
    items.push({
        label: 'def',
        kind: 'keyword',
        sortText: '0_def_import',
    });
    items.push({
        label: 'event',
        kind: 'keyword',
        sortText: '0_event_import',
    });
    const resolved = await getImportWorkspaceIndex().resolveImportsForDocument(document);
    const target = resolved.find(item => item.sourcePath === activeImport.sourcePath);
    if (!target) {
        return {matched, items};
    }

    for (const variableName of target.explicitVariables) {
        items.push({
            label: variableName,
            kind: 'variable',
            detail: 'Imported variable',
            sortText: `3_import_var_${variableName}`,
        });
    }

    for (const eventPath of target.absoluteEvents) {
        items.push({
            label: eventPath,
            kind: 'event',
            detail: 'Imported absolute event',
            sortText: `5_import_event_${eventPath}`,
        });
    }

    return {matched, items};
}

function pushUniqueCompletion(
    items: FcstmCompletionItem[],
    seen: Set<string>,
    item: FcstmCompletionItem
): void {
    const key = `${item.kind}:${item.label}:${item.insertText || ''}`;
    if (seen.has(key)) {
        return;
    }

    seen.add(key);
    items.push(item);
}

function resolveAbsoluteStatePath(
    semantic: FcstmSemanticDocument,
    pathSegments: string[]
): FcstmSemanticState | undefined {
    let current = findRootState(semantic);
    if (!current) {
        return undefined;
    }

    // Grammar allows both `/Child.Grandchild` (root-relative) and
    // `/Root.Child.Grandchild` (explicit root prefix). If the first segment
    // matches the root state name, treat it as the root itself and descend
    // from there; otherwise descend from the root as usual.
    let segments = pathSegments;
    if (segments.length > 0 && segments[0] === current.name) {
        segments = segments.slice(1);
    }

    for (const segment of segments) {
        const next = semantic.states.find(item => (
            item.parentStateId === current?.identity.id
            && item.name === segment
        ));
        if (!next) {
            return undefined;
        }
        current = next;
    }

    return current;
}

function collectAbsolutePathCompletions(
    semantic: FcstmSemanticDocument,
    rawPath: string,
    position: TextPositionLike
): FcstmContextCompletionResult {
    const normalizedPath = rawPath.startsWith('/') ? rawPath.slice(1) : rawPath;
    const pathParts = normalizedPath ? normalizedPath.split('.') : [];
    const endsWithDot = normalizedPath.endsWith('.');
    const partial = endsWithDot ? '' : (pathParts.pop() || '');
    const parentSegments = pathParts.filter(Boolean);
    const containerState = resolveAbsoluteStatePath(semantic, parentSegments);
    if (!containerState) {
        return {matched: true, items: []};
    }

    const pathPrefix = parentSegments.length > 0
        ? `/${parentSegments.join('.')}.`
        : '/';
    const items: FcstmCompletionItem[] = [];
    pushChildStateNames(semantic, containerState, items, {
        pathPrefix,
        insertTextPrefix: '',
        partial,
        sortPrefix: '4_abs_state',
        detailPrefix: 'Absolute state path',
    });
    pushVisibleScopedEvents(semantic, containerState, 'absolute', items, {
        position,
        pathPrefix,
        insertTextPrefix: '',
        partial,
        sortPrefix: '5_abs_event',
        detailPrefix: 'Absolute event path',
    });

    return {matched: true, items};
}

// ---------------------------------------------------------------------------
// Block-context detection: is the cursor strictly inside an operation block
// (enter/during/exit/effect body) or inside a transition guard expression?
// Complements token-based detection by handling multi-line bodies.
// ---------------------------------------------------------------------------

type BlockContextKind = 'operationBlock' | 'guardBody';

interface BlockContext {
    kind: BlockContextKind;
    range: TextRange;
}

function comparePositionsHere(a: TextPositionLike, b: TextPositionLike): number {
    if (a.line !== b.line) {
        return a.line - b.line;
    }
    return a.character - b.character;
}

function normalizeRange(range: TextRange): TextRange {
    return comparePositionsHere(range.start, range.end) <= 0
        ? range
        : {start: range.end, end: range.start};
}

function rangeStrictlyContains(range: TextRange | undefined, pos: TextPositionLike): boolean {
    if (!range) {
        return false;
    }
    const norm = normalizeRange(range);
    if (comparePositionsHere(pos, norm.start) <= 0) {
        return false;
    }
    if (comparePositionsHere(pos, norm.end) >= 0) {
        return false;
    }
    return true;
}

function detectBlockContext(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): BlockContext | undefined {
    let best: BlockContext | undefined;
    const tighter = (range: TextRange): boolean =>
        !best || rangeLength(range) < rangeLength(best.range);

    const acceptBody = (range: TextRange): boolean => {
        const norm = normalizeRange(range);
        if (!rangeStrictlyContains(norm, position)) {
            return false;
        }
        // Exclude the opening-brace line and the closing-brace line so we
        // only fire inside the body proper.
        return position.line > norm.start.line && position.line < norm.end.line;
    };

    // Action bodies (enter/during/exit, plain or aspect). `ast.operationBlock.range`
    // can be inverted or report inner if-blocks on nested cases, so we use
    // `action.range` with the line-exclusion heuristic above.
    for (const action of semantic.actions) {
        if (action.mode !== 'operations') {
            continue;
        }
        const range = normalizeRange(action.range);
        if (!acceptBody(range) || !tighter(range)) {
            continue;
        }
        best = {kind: 'operationBlock', range};
    }
    // Transition effect blocks.
    for (const transition of semantic.transitions) {
        const effect = (transition.ast as { effect?: { range?: TextRange } } | undefined)?.effect;
        if (!effect?.range) {
            continue;
        }
        const range = normalizeRange(effect.range);
        if (!acceptBody(range) || !tighter(range)) {
            continue;
        }
        best = {kind: 'operationBlock', range};
    }
    // Guard expressions on transitions.
    for (const transition of semantic.transitions) {
        const guard = transition.guard;
        if (!guard?.range) {
            continue;
        }
        const range = normalizeRange(guard.range);
        if (rangeStrictlyContains(range, position) && tighter(range)) {
            best = {kind: 'guardBody', range};
        }
    }
    return best;
}

// ---------------------------------------------------------------------------
// Narrow keyword helpers. Each returns a tightly-scoped keyword subset with
// consistent sort priority so that they surface before identifier matches.
// ---------------------------------------------------------------------------

function pickKeywordItems(names: string[]): FcstmCompletionItem[] {
    return names.map((name, index) => ({
        label: name,
        kind: 'keyword',
        sortText: `0_${String(index).padStart(2, '0')}_${name}`,
    }));
}

function getOperationBlockKeywords(): FcstmCompletionItem[] {
    return pickKeywordItems(['if', 'else']);
}

function getGuardBodyKeywords(): FcstmCompletionItem[] {
    return pickKeywordItems(['and', 'or', 'not', 'true', 'false']);
}

function getPostTransitionTargetKeywords(): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = [];
    items.push({label: '::', kind: 'keyword', detail: 'Local event scope', insertText: ':: ', sortText: '0_00_dc'});
    items.push({label: ':', kind: 'keyword', detail: 'Chain event / guard prefix', insertText: ': ', sortText: '0_01_c'});
    items.push(...pickKeywordItems(['if', 'effect']));
    return items;
}

function getPostTransitionTriggerKeywords(): FcstmCompletionItem[] {
    // After a completed event trigger (`:: Event │` or `: Event │`), the
    // grammar allows an optional `effect { … }` block. Guards after an
    // event are not allowed, so `if` is deliberately excluded.
    return pickKeywordItems(['effect']);
}

function getAspectAfterShiftKeywords(partial?: string): FcstmCompletionItem[] {
    return pickKeywordItems(['during']).filter(item => matchesPartial(item.label, partial || ''));
}

function getAspectAfterDuringKeywords(partial?: string): FcstmCompletionItem[] {
    return pickKeywordItems(['before', 'after']).filter(item => matchesPartial(item.label, partial || ''));
}

function getAspectAfterBeforeAfterKeywords(partial?: string): FcstmCompletionItem[] {
    return pickKeywordItems(['abstract']).filter(item => matchesPartial(item.label, partial || ''));
}

function getLifecycleAfterStageKeywords(
    stage: 'enter' | 'during' | 'exit',
    partial?: string
): FcstmCompletionItem[] {
    const base = stage === 'during' ? ['before', 'after', 'abstract', 'ref'] : ['abstract', 'ref'];
    return pickKeywordItems(base).filter(item => matchesPartial(item.label, partial || ''));
}

function getPostGuardCloseKeywords(partial?: string): FcstmCompletionItem[] {
    return pickKeywordItems(['effect']).filter(item => matchesPartial(item.label, partial || ''));
}

function getPostEffectKeywordItems(): FcstmCompletionItem[] {
    // After `effect` the only valid follow-up is `{`. VSCode's auto-bracket
    // feature handles this — no visible completion is preferable to noise.
    return [];
}

function getAfterIfKeywordItems(): FcstmCompletionItem[] {
    // After `if` the only valid follow-up is `[`. Same rationale as above.
    return [];
}

async function pushVariableAndMathCompletions(
    semantic: FcstmSemanticDocument | undefined,
    document: TextDocumentLike | undefined,
    position: TextPositionLike,
    items: FcstmCompletionItem[],
    seen: Set<string>
): Promise<void> {
    if (semantic) {
        for (const variable of semantic.variables) {
            pushUniqueCompletion(items, seen, {
                label: variable.name,
                kind: 'variable',
                sortText: `3_${variable.name}`,
            });
        }
    } else if (document) {
        // Semantic may be unavailable when the current line leaves the
        // document mid-parse (e.g. `def int x = │`). Fall back to the raw
        // parse-tree symbol list so declared variables still surface.
        const fallback = await getDocumentSymbolCompletions(document);
        for (const item of fallback) {
            if (item.kind === 'variable') {
                pushUniqueCompletion(items, seen, item);
            }
        }
    }
    for (const item of getConstantCompletions()) {
        pushUniqueCompletion(items, seen, item);
    }
    for (const item of getFunctionCompletions()) {
        pushUniqueCompletion(items, seen, item);
    }
    void position;
}

// ---------------------------------------------------------------------------
// Main context dispatch.
// ---------------------------------------------------------------------------

async function collectContextAwareCompletions(
    semantic: FcstmSemanticDocument | undefined,
    document: TextDocumentLike,
    position: TextPositionLike,
    lineTokens: LexToken[],
    beforeCursor: string
): Promise<FcstmContextCompletionResult> {
    const items: FcstmCompletionItem[] = [];
    const seen = new Set<string>();
    const lookupStates = semantic ? collectLookupStates(semantic, position) : [];
    const currentScope = semantic ? getCurrentScopeState(semantic, position) : undefined;

    // Block context wins over per-line heuristics because it is derived from
    // the semantic model and reliably spans multi-line blocks.
    const blockContext = semantic ? detectBlockContext(semantic, position) : undefined;
    if (blockContext?.kind === 'guardBody') {
        for (const item of getGuardBodyKeywords()) {
            pushUniqueCompletion(items, seen, item);
        }
        await pushVariableAndMathCompletions(semantic, document, position, items, seen);
        return {matched: true, items};
    }
    if (blockContext?.kind === 'operationBlock') {
        for (const item of getOperationBlockKeywords()) {
            pushUniqueCompletion(items, seen, item);
        }
        await pushVariableAndMathCompletions(semantic, document, position, items, seen);
        return {matched: true, items};
    }

    const syntaxContext = extractSyntaxCompletionContextFromLineTokens(
        lineTokens,
        semantic,
        position,
        beforeCursor
    );

    if (syntaxContext.kind === 'absoluteEventPath') {
        if (!semantic) {
            return {matched: true, items: []};
        }
        return collectAbsolutePathCompletions(semantic, syntaxContext.rawPath, position);
    }

    if (syntaxContext.kind === 'pseudoStateMarker') {
        pushPseudoStateMarker(items, syntaxContext.partial);
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'actionRef') {
        if (semantic) {
            pushVisibleNamedActions(semantic, lookupStates, items);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'localEvent') {
        if (semantic) {
            const insertTextPrefix = getTriggerInsertTextPrefix(
                beforeCursor,
                findTransitionOperatorToken(lineTokens, '::')
            );
            const sourceState = syntaxContext.transition?.sourceStateId
                ? findStateById(semantic, syntaxContext.transition.sourceStateId)
                : resolveVisibleStateReference(semantic, lookupStates, syntaxContext.sourceStateName || syntaxContext.transition?.sourceStateName);
            pushVisibleScopedEvents(semantic, sourceState, 'local', items, {
                position,
                insertTextPrefix,
                partial: syntaxContext.partial,
                sortPrefix: '5_local_event',
            });
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'chainEvent') {
        if (semantic) {
            const insertTextPrefix = getTriggerInsertTextPrefix(
                beforeCursor,
                findTransitionOperatorToken(lineTokens, ':')
            );
            const ownerState = syntaxContext.transition
                ? findStateById(semantic, syntaxContext.transition.ownerStateId)
                : currentScope;
            pushVisibleScopedEvents(semantic, ownerState, 'chain', items, {
                position,
                insertTextPrefix,
                partial: syntaxContext.partial,
                sortPrefix: '5_chain_event',
            });
        }
        // Offer `if` / `/` alongside chain events ONLY when the user has
        // already put a space after the colon — otherwise stay pure events.
        const postColonHasSpace = /:\s+$/.test(beforeCursor);
        if (!syntaxContext.partial && postColonHasSpace) {
            for (const item of pickKeywordItems(['if', '/'])) {
                pushUniqueCompletion(items, seen, item);
            }
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'transitionTarget') {
        pushPseudoStateMarker(items, syntaxContext.partial);
        if (semantic) {
            // Don't filter by partial here — VSCode's fuzzy matcher is
            // stronger than our prefix match.
            pushChildStateNames(semantic, currentScope, items, {
                includeSelf: false,
                sortPrefix: '4_target_state',
            });
            pushVisibleImportAliases(semantic, currentScope, items);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'postTransitionTarget') {
        for (const item of getPostTransitionTargetKeywords()) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'postTransitionTrigger') {
        for (const item of getPostTransitionTriggerKeywords()) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'afterIfKeyword') {
        for (const item of getAfterIfKeywordItems()) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'postGuardClose') {
        for (const item of getPostGuardCloseKeywords(syntaxContext.partial)) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'postEffectKeyword') {
        for (const item of getPostEffectKeywordItems()) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'guardBody') {
        for (const item of getGuardBodyKeywords()) {
            pushUniqueCompletion(items, seen, item);
        }
        await pushVariableAndMathCompletions(semantic, document, position, items, seen);
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'inEffectBody') {
        for (const item of getOperationBlockKeywords()) {
            pushUniqueCompletion(items, seen, item);
        }
        await pushVariableAndMathCompletions(semantic, document, position, items, seen);
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'aspectAfterShift') {
        for (const item of getAspectAfterShiftKeywords(syntaxContext.partial)) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'aspectAfterDuring') {
        for (const item of getAspectAfterDuringKeywords(syntaxContext.partial)) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'aspectAfterBeforeAfter') {
        for (const item of getAspectAfterBeforeAfterKeywords(syntaxContext.partial)) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'lifecycleAfterStage') {
        for (const item of getLifecycleAfterStageKeywords(syntaxContext.stage, syntaxContext.partial)) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'lifecycleAfterAbstract') {
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'identifierSlot') {
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'variableDefinitionRhs') {
        await pushVariableAndMathCompletions(semantic, document, position, items, seen);
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'defTypeKeyword') {
        for (const item of pickKeywordItems(['int', 'float'])) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'postPseudoKeyword') {
        for (const item of pickKeywordItems(['state'])) {
            pushUniqueCompletion(items, seen, item);
        }
        return {matched: true, items};
    }

    if (syntaxContext.kind === 'postForcedSource') {
        // After `!State │` / `!* │` the only valid follow-up is the `->` arrow.
        items.push({
            label: '->',
            kind: 'keyword',
            detail: 'Transition arrow',
            insertText: '-> ',
            sortText: '0_00_arrow',
        });
        return {matched: true, items};
    }

    return {matched: false, items: []};
}

// ---------------------------------------------------------------------------
// Narrow fallback keyword sets.
// ---------------------------------------------------------------------------

function getTopLevelStarterCompletions(): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = pickKeywordItems(['def', 'import', 'state', 'pseudo', 'event']);
    items.push({
        label: '[*]',
        kind: 'keyword',
        detail: 'Pseudo-state marker',
        insertText: '[*]',
        sortText: '0_50_init_marker',
    });
    return items;
}

function getStateBodyStarterCompletions(): FcstmCompletionItem[] {
    const items: FcstmCompletionItem[] = pickKeywordItems([
        'state', 'pseudo', 'event', 'enter', 'during', 'exit', 'import',
    ]);
    items.push({
        label: '>>',
        kind: 'keyword',
        detail: 'Aspect marker (>> during before|after)',
        insertText: '>> ',
        sortText: '0_40_aspect',
    });
    items.push({
        label: '[*]',
        kind: 'keyword',
        detail: 'Pseudo-state marker',
        insertText: '[*]',
        sortText: '0_50_init_marker',
    });
    items.push({
        label: '!',
        kind: 'keyword',
        detail: 'Forced-transition marker (! / !*)',
        insertText: '!',
        sortText: '0_60_forced',
    });
    return items;
}

function isInsideAnyStateBody(
    semantic: FcstmSemanticDocument,
    position: TextPositionLike
): boolean {
    return semantic.states.some(state => rangeStrictlyContains(state.range, position));
}

/**
 * Fallback structural check: the semantic document's state ranges get
 * truncated when a state body is left unclosed mid-edit (`state Root {│`).
 * Count outstanding `{`s in the raw text before the cursor, skipping
 * comments and strings. If any are still open, the cursor is inside a
 * composite/lifecycle body for fallback-narrowing purposes.
 */
function hasUnbalancedOpeningBrace(
    document: TextDocumentLike,
    position: TextPositionLike
): boolean {
    let text = '';
    for (let line = 0; line < position.line; line++) {
        text += document.lineAt(line).text + '\n';
    }
    const currentLine = document.lineAt(position.line).text;
    text += currentLine.substring(0, position.character);

    let depth = 0;
    let inLineComment = false;
    let inBlockComment = false;
    let inDouble = false;
    let inSingle = false;

    for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        const next = text[i + 1];
        if (inLineComment) {
            if (ch === '\n') {
                inLineComment = false;
            }
            continue;
        }
        if (inBlockComment) {
            if (ch === '*' && next === '/') {
                inBlockComment = false;
                i++;
            }
            continue;
        }
        if (inDouble) {
            if (ch === '\\') {
                i++;
                continue;
            }
            if (ch === '"') {
                inDouble = false;
            }
            continue;
        }
        if (inSingle) {
            if (ch === '\\') {
                i++;
                continue;
            }
            if (ch === '\'') {
                inSingle = false;
            }
            continue;
        }
        if (ch === '/' && next === '/') {
            inLineComment = true;
            i++;
            continue;
        }
        if (ch === '/' && next === '*') {
            inBlockComment = true;
            i++;
            continue;
        }
        if (ch === '#') {
            inLineComment = true;
            continue;
        }
        if (ch === '"') {
            inDouble = true;
            continue;
        }
        if (ch === '\'') {
            inSingle = true;
            continue;
        }
        if (ch === '{') {
            depth++;
        } else if (ch === '}') {
            depth--;
        }
    }

    return depth > 0;
}

export async function collectCompletionItems(
    document: TextDocumentLike,
    position: TextPositionLike
): Promise<FcstmCompletionItem[]> {
    const items: FcstmCompletionItem[] = [];
    const seen = new Set<string>();
    const lineText = document.lineAt(position.line).text;
    const beforeCursor = lineText.substring(0, position.character);

    if (isInComment(beforeCursor) || isInString(beforeCursor)) {
        return items;
    }

    const semantic = await getWorkspaceGraph().getSemanticDocument(document);
    const lineTokens = await getParser().lex(beforeCursor);
    const importAware = await getImportAwareCompletions(document, position, lineTokens);
    const contextAware = await collectContextAwareCompletions(
        semantic || undefined,
        document,
        position,
        lineTokens,
        beforeCursor
    );

    if (importAware.matched || contextAware.matched) {
        for (const item of contextAware.items) {
            pushUniqueCompletion(items, seen, item);
        }
        for (const item of importAware.items) {
            pushUniqueCompletion(items, seen, item);
        }
        return items;
    }

    // Narrow fallback: offer starters appropriate to the structural context,
    // rather than dumping every keyword / constant / function.
    const insideState = (semantic && isInsideAnyStateBody(semantic, position))
        || hasUnbalancedOpeningBrace(document, position);
    const starterKeywords = insideState
        ? getStateBodyStarterCompletions()
        : getTopLevelStarterCompletions();
    for (const item of starterKeywords) {
        pushUniqueCompletion(items, seen, item);
    }

    if (semantic) {
        for (const item of collectScopedSymbolCompletions(semantic, position)) {
            pushUniqueCompletion(items, seen, item);
        }
    } else {
        for (const item of await getDocumentSymbolCompletions(document)) {
            pushUniqueCompletion(items, seen, item);
        }
    }

    return items;
}
