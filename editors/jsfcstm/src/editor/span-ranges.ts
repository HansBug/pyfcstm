import {createRange, type TextRange} from '../utils/text';

export function spanToRange(value: unknown): TextRange | null {
    if (typeof value !== 'object' || value === null) return null;
    const obj = value as Record<string, unknown>;
    const start = obj.start as Record<string, unknown> | undefined;
    const end = obj.end as Record<string, unknown> | undefined;
    if (
        typeof start?.line === 'number' &&
        typeof start?.character === 'number' &&
        typeof end?.line === 'number' &&
        typeof end?.character === 'number'
    ) {
        return createRange(start.line, start.character, end.line, end.character);
    }
    if (typeof obj.line !== 'number' || typeof obj.column !== 'number') return null;
    if (!Number.isInteger(obj.line) || !Number.isInteger(obj.column)) return null;
    if (obj.line < 1 || obj.column < 1) return null;

    const startLine = obj.line - 1;
    const startColumn = obj.column - 1;
    const rawEndLine = obj.end_line;
    const rawEndColumn = obj.end_column;
    const endLine = typeof rawEndLine === 'number' ? rawEndLine - 1 : startLine;
    const endColumn = typeof rawEndColumn === 'number' ? rawEndColumn - 1 : startColumn;
    if (
        !Number.isInteger(endLine) ||
        !Number.isInteger(endColumn) ||
        endLine < startLine ||
        (endLine === startLine && endColumn < startColumn)
    ) {
        return null;
    }

    return createRange(startLine, startColumn, endLine, endColumn);
}
