const packageJson = require('../package.json') as {
    name: string;
    version: string;
    description: string;
};

export type {
    FcstmDiagnostic,
    FcstmDiagnosticSeverity,
    ParseTreeNode,
    TextDocumentLike,
    TextLineLike,
    TextPositionLike,
    TextRange,
    TokenLike,
} from './text';
export {
    cloneRange,
    createRange,
    fallbackRangeFromText,
    getDocumentFilePath,
    makeNodeRange,
    makeTokenRange,
    rangeContains,
    tokenText,
} from './text';
export type {ParseError, ParseResult} from './parser';
export {FcstmParser, getParser} from './parser';
export type {
    ImportCycle,
    ImportEntry,
    ParsedDocumentInfo,
    ResolvedImportTarget,
} from './imports';
export {
    FcstmImportWorkspaceIndex,
    getImportWorkspaceIndex,
    resolveImportReference,
} from './imports';
export type {
    FcstmCollectedSymbols,
    FcstmDocumentSymbol,
    FcstmSymbolKind,
} from './symbols';
export {
    collectDocumentSymbols,
    collectSymbolsFromTree,
    extractDocumentSymbolsFromTree,
} from './symbols';
export type {FcstmCompletionItem, FcstmCompletionKind} from './completion';
export {
    collectCompletionItems,
    isInComment,
    isInString,
    KEYWORDS,
    MATH_CONSTANTS,
    MATH_FUNCTIONS,
} from './completion';
export type {FcstmHoverDoc, FcstmHoverResult} from './hover';
export {
    findHoverInfo,
    HOVER_DOCS,
    resolveHover,
} from './hover';
export {
    collectDocumentDiagnostics,
    convertParseErrorToDiagnostic,
} from './diagnostics';

export interface JsFcstmPackageInfo {
    name: string;
    version: string;
    description: string;
}

/**
 * Return the metadata exposed by the jsfcstm skeleton package.
 *
 * Phase 0/1 intentionally keeps the public API minimal. The immediate goal is
 * to establish a publishable, testable npm package boundary before migrating
 * FCSTM language logic into this package in later phases.
 */
export function getJsFcstmPackageInfo(): JsFcstmPackageInfo {
    return {
        name: packageJson.name,
        version: packageJson.version,
        description: packageJson.description,
    };
}

export const JSFCSTM_PACKAGE_NAME = packageJson.name;
export const JSFCSTM_PACKAGE_VERSION = packageJson.version;
