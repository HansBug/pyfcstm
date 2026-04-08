import {SemanticTokensBuilder} from 'vscode-languageserver/node';
import type {SemanticTokens, SemanticTokensLegend} from 'vscode-languageserver/node';

import {TextDocumentLike} from '../utils/text';
import {collectSymbolOccurrences} from './references';

export const FCSTM_SEMANTIC_TOKEN_TYPES = [
    'keyword',
    'type',
    'class',
    'function',
    'variable',
    'property',
    'namespace',
    'string',
    'comment',
    'operator',
] as const;

export const FCSTM_SEMANTIC_TOKEN_MODIFIERS: string[] = [];

export type FcstmSemanticTokenType = typeof FCSTM_SEMANTIC_TOKEN_TYPES[number];

interface FcstmSemanticToken {
    line: number;
    character: number;
    length: number;
    type: FcstmSemanticTokenType;
    modifierMask: number;
}

const TOKEN_TYPE_TO_INDEX = new Map(
    FCSTM_SEMANTIC_TOKEN_TYPES.map((item, index) => [item, index])
);

const KEYWORDS = [
    'state',
    'pseudo',
    'named',
    'def',
    'event',
    'import',
    'as',
    'enter',
    'during',
    'exit',
    'before',
    'after',
    'abstract',
    'ref',
    'effect',
    'if',
    'else',
    'and',
    'or',
    'not',
];

const TYPES = ['int', 'float'];
const OPERATORS = ['::', '->', '>>', ':', '/', '[*]'];
const KEYWORD_RE = /\b[A-Za-z_][A-Za-z0-9_]*\b/g;
const STRING_RE = /"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g;

function pushToken(tokens: FcstmSemanticToken[], token: FcstmSemanticToken): void {
    if (token.length <= 0) {
        return;
    }
    tokens.push(token);
}

function tokenTypeIndex(type: FcstmSemanticTokenType): number {
    return TOKEN_TYPE_TO_INDEX.get(type) || 0;
}

function collectCommentAndStringTokens(document: TextDocumentLike): FcstmSemanticToken[] {
    const tokens: FcstmSemanticToken[] = [];
    const lines = document.getText().split('\n');
    let inBlockComment = false;

    for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
        const line = lines[lineIndex];

        if (inBlockComment) {
            const endIndex = line.indexOf('*/');
            const length = endIndex >= 0 ? endIndex + 2 : line.length;
            pushToken(tokens, {
                line: lineIndex,
                character: 0,
                length: Math.max(1, length),
                type: 'comment',
                modifierMask: 0,
            });
            inBlockComment = endIndex < 0;
            if (inBlockComment) {
                continue;
            }
        }

        const lineCommentIndex = line.indexOf('//');
        const hashCommentIndex = line.indexOf('#');
        const commentIndices = [lineCommentIndex, hashCommentIndex].filter(index => index >= 0);
        if (commentIndices.length > 0) {
            const commentIndex = Math.min.apply(null, commentIndices);
            pushToken(tokens, {
                line: lineIndex,
                character: commentIndex,
                length: line.length - commentIndex,
                type: 'comment',
                modifierMask: 0,
            });
        }

        const blockStart = line.indexOf('/*');
        if (blockStart >= 0) {
            const blockEnd = line.indexOf('*/', blockStart + 2);
            pushToken(tokens, {
                line: lineIndex,
                character: blockStart,
                length: blockEnd >= 0 ? (blockEnd + 2 - blockStart) : (line.length - blockStart),
                type: 'comment',
                modifierMask: 0,
            });
            inBlockComment = blockEnd < 0;
        }

        STRING_RE.lastIndex = 0;
        let stringMatch: RegExpExecArray | null;
        while ((stringMatch = STRING_RE.exec(line)) !== null) {
            pushToken(tokens, {
                line: lineIndex,
                character: stringMatch.index,
                length: stringMatch[0].length,
                type: 'string',
                modifierMask: 0,
            });
        }
    }

    return tokens;
}

function overlapsExisting(tokens: FcstmSemanticToken[], candidate: FcstmSemanticToken): boolean {
    return tokens.some(item => (
        item.line === candidate.line
        && candidate.character < item.character + item.length
        && item.character < candidate.character + candidate.length
    ));
}

function collectKeywordAndOperatorTokens(
    document: TextDocumentLike,
    baseTokens: FcstmSemanticToken[]
): FcstmSemanticToken[] {
    const tokens = [...baseTokens];
    const lines = document.getText().split('\n');

    for (let lineIndex = 0; lineIndex < lines.length; lineIndex++) {
        const line = lines[lineIndex];

        KEYWORD_RE.lastIndex = 0;
        let wordMatch: RegExpExecArray | null;
        while ((wordMatch = KEYWORD_RE.exec(line)) !== null) {
            const text = wordMatch[0];
            const type = TYPES.includes(text)
                ? 'type'
                : KEYWORDS.includes(text)
                    ? 'keyword'
                    : null;
            if (!type) {
                continue;
            }

            const token: FcstmSemanticToken = {
                line: lineIndex,
                character: wordMatch.index,
                length: text.length,
                type,
                modifierMask: 0,
            };
            if (!overlapsExisting(tokens, token)) {
                tokens.push(token);
            }
        }

        for (const operator of OPERATORS) {
            let searchIndex = line.indexOf(operator);
            while (searchIndex >= 0) {
                const token: FcstmSemanticToken = {
                    line: lineIndex,
                    character: searchIndex,
                    length: operator.length,
                    type: 'operator',
                    modifierMask: 0,
                };
                if (!overlapsExisting(tokens, token)) {
                    tokens.push(token);
                }
                searchIndex = line.indexOf(operator, searchIndex + operator.length);
            }
        }
    }

    return tokens;
}

async function collectSymbolTokens(document: TextDocumentLike): Promise<FcstmSemanticToken[]> {
    const occurrences = await collectSymbolOccurrences(document);
    return occurrences
        .filter(item => item.filePath === (document.filePath || document.uri?.fsPath || ''))
        .map(item => {
            let type: FcstmSemanticTokenType = 'variable';
            if (item.kind === 'state') {
                type = 'class';
            } else if (item.kind === 'action') {
                type = 'function';
            } else if (item.kind === 'event') {
                type = 'property';
            } else if (item.kind === 'import') {
                type = 'namespace';
            }

            return {
                line: item.range.start.line,
                character: item.range.start.character,
                length: item.range.end.character - item.range.start.character,
                type,
                modifierMask: 0,
            };
        });
}

function sortTokens(tokens: FcstmSemanticToken[]): FcstmSemanticToken[] {
    return [...tokens].sort((left, right) => (
        left.line - right.line
        || left.character - right.character
        || left.length - right.length
    ));
}

/**
 * Return the semantic-token legend exported by the jsfcstm language server.
 */
export function getFcstmSemanticTokensLegend(): SemanticTokensLegend {
    return {
        tokenTypes: [...FCSTM_SEMANTIC_TOKEN_TYPES],
        tokenModifiers: [...FCSTM_SEMANTIC_TOKEN_MODIFIERS],
    };
}

/**
 * Collect semantic tokens for an FCSTM document.
 */
export async function collectSemanticTokens(
    document: TextDocumentLike
): Promise<SemanticTokens> {
    const builder = new SemanticTokensBuilder();
    const commentAndStringTokens = collectCommentAndStringTokens(document);
    const lexicalTokens = collectKeywordAndOperatorTokens(document, commentAndStringTokens);
    const symbolTokens = await collectSymbolTokens(document);
    const tokens = sortTokens([...lexicalTokens, ...symbolTokens]);

    const seen = new Set<string>();
    for (const token of tokens) {
        const key = [token.line, token.character, token.length, token.type].join(':');
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);
        builder.push(
            token.line,
            token.character,
            token.length,
            tokenTypeIndex(token.type),
            token.modifierMask
        );
    }

    return builder.build();
}
