import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import type * as JsFcstmPackage from '@pyfcstm/jsfcstm';
import type * as EditorModule from '@pyfcstm/jsfcstm/editor';
import type * as DslModule from '@pyfcstm/jsfcstm/dsl';
import type * as WorkspaceModule from '@pyfcstm/jsfcstm/workspace';

export const packageJson = require('../package.json') as {
    name: string;
    version: string;
    description: string;
};

export const packageModule = require('@pyfcstm/jsfcstm') as typeof JsFcstmPackage;
export const editorModule = require('@pyfcstm/jsfcstm/editor') as typeof EditorModule;
export const dslModule = require('@pyfcstm/jsfcstm/dsl') as typeof DslModule;
export const workspaceModule = require('@pyfcstm/jsfcstm/workspace') as typeof WorkspaceModule;
export const parserModule = dslModule;
export const importsModule = workspaceModule;
export const symbolsModule = editorModule;
export const completionModule = editorModule;
export const hoverModule = editorModule;

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
    const descriptor = Object.getOwnPropertyDescriptor(target, key);
    const original = target[key];

    if (descriptor && !descriptor.writable) {
        Object.defineProperty(target, key, {
            configurable: true,
            enumerable: descriptor.enumerable ?? true,
            writable: true,
            value,
        });
    } else {
        (target as T)[key] = value;
    }

    try {
        return await fn();
    } finally {
        if (descriptor && !descriptor.writable) {
            Object.defineProperty(target, key, descriptor);
        } else {
            (target as T)[key] = original;
        }
    }
}
