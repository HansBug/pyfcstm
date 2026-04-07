import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import type * as JsFcstmPackage from '../dist/index';
import type * as CompletionModule from '../dist/completion';
import type * as HoverModule from '../dist/hover';
import type * as ImportsModule from '../dist/imports';
import type * as ParserModule from '../dist/parser';
import type * as SymbolsModule from '../dist/symbols';

export const packageJson = require('../package.json') as {
    name: string;
    version: string;
    description: string;
};

export const packageModule = require('../dist/index.js') as typeof JsFcstmPackage;
export const parserModule = require('../dist/parser.js') as typeof ParserModule;
export const importsModule = require('../dist/imports.js') as typeof ImportsModule;
export const symbolsModule = require('../dist/symbols.js') as typeof SymbolsModule;
export const completionModule = require('../dist/completion.js') as typeof CompletionModule;
export const hoverModule = require('../dist/hover.js') as typeof HoverModule;

const tempDirs: string[] = [];

afterEach(() => {
    while (tempDirs.length > 0) {
        const dir = tempDirs.pop();
        if (dir) {
            fs.rmSync(dir, {recursive: true, force: true});
        }
    }
});

export function trackTempDir(prefix: string): string {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    tempDirs.push(dir);
    return dir;
}

export function writeFile(filePath: string, text: string): void {
    fs.mkdirSync(path.dirname(filePath), {recursive: true});
    fs.writeFileSync(filePath, text);
}

export function createDocument(
    text: string,
    filePath: string
): JsFcstmPackage.TextDocumentLike & {
    uri: { fsPath: string; toString(): string };
} {
    const lines = text.split('\n');
    return {
        filePath,
        uri: {
            fsPath: filePath,
            toString() {
                return this.fsPath;
            },
        },
        lineCount: lines.length,
        getText() {
            return text;
        },
        lineAt(line: number) {
            return {
                text: lines[line] || '',
            };
        },
    };
}

export function createToken(
    text: string,
    line = 1,
    column = 0
): JsFcstmPackage.TokenLike {
    return {text, line, column};
}

export function createLeafTextNode(text: string): JsFcstmPackage.ParseTreeNode {
    return {
        children: [],
        getText() {
            return text;
        },
    };
}

export function createNode(
    name: string,
    children: JsFcstmPackage.ParseTreeNode[] = [],
    extra: Partial<JsFcstmPackage.ParseTreeNode> = {}
): JsFcstmPackage.ParseTreeNode {
    return {
        constructor: {name},
        children,
        ...extra,
    };
}

export async function withPatchedProperty<T extends object, K extends keyof T, R>(
    target: T,
    key: K,
    value: T[K],
    fn: () => Promise<R> | R
): Promise<R> {
    const original = target[key];
    (target as T)[key] = value;

    try {
        return await fn();
    } finally {
        (target as T)[key] = original;
    }
}
