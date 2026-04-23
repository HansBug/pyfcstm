import * as vscode from 'vscode';
import {resolveHover} from '@pyfcstm/jsfcstm';
import {toVscodeRange} from './vscode-converters';

export class FcstmHoverProvider implements vscode.HoverProvider {
    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        _token: vscode.CancellationToken
    ): Thenable<vscode.Hover | null> | vscode.Hover | null {
        return this.provideHoverInternal(document, position);
    }

    private async provideHoverInternal(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<vscode.Hover | null> {
        const hover = await resolveHover(document, position);
        if (!hover) {
            return null;
        }

        if (hover.kind === 'doc') {
            const markdown = new vscode.MarkdownString();
            markdown.appendMarkdown(`**${hover.doc.title}**\n\n`);
            markdown.appendMarkdown(`${hover.doc.description}\n\n`);
            if (hover.doc.example) {
                markdown.appendMarkdown(`**Example:**\n\n${hover.doc.example}`);
            }
            return new vscode.Hover(markdown);
        }

        const markdown = new vscode.MarkdownString();
        markdown.appendMarkdown(`**${hover.title}**\n\n`);
        markdown.appendMarkdown(`Path: \`${hover.sourcePath}\`\n\n`);
        if (hover.entryFile) {
            markdown.appendMarkdown(`Resolved file: \`${hover.entryFile}\`\n\n`);
        } else if (hover.resolvedFile) {
            markdown.appendMarkdown(`Resolved path: \`${hover.resolvedFile}\`\n\n`);
        }
        if (hover.rootStateName) {
            markdown.appendMarkdown(`Root state: \`${hover.rootStateName}\`\n\n`);
        }
        if (hover.explicitVariables.length > 0) {
            markdown.appendMarkdown(`Variables: \`${hover.explicitVariables.join('`, `')}\`\n\n`);
        }
        if (hover.absoluteEvents.length > 0) {
            markdown.appendMarkdown(`Absolute events: \`${hover.absoluteEvents.join('`, `')}\``);
        }
        return new vscode.Hover(markdown, toVscodeRange(hover.range));
    }
}
