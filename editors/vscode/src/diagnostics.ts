import * as vscode from 'vscode';
import {collectDocumentDiagnosticsByUri} from '@pyfcstm/jsfcstm';
import type {FcstmDiagnostic} from '@pyfcstm/jsfcstm';
import {toVscodeDiagnostic} from './vscode-converters';

type DiagnosticPublications = Map<string, FcstmDiagnostic[]> & {
    authoritativeTargets?: ReadonlySet<string>;
};

function diagnosticContributionKey(diagnostic: FcstmDiagnostic): string {
    return JSON.stringify([
        diagnostic.code ?? null,
        diagnostic.severity ?? null,
        diagnostic.source ?? null,
        diagnostic.range,
        diagnostic.data ?? null,
        diagnostic.relatedInformation ?? null,
    ]);
}

function unreachableTransitionAuthoredKey(diagnostic: FcstmDiagnostic): string | null {
    if (
        diagnostic.code !== 'W_UNREACHABLE_TRANSITION'
        || !diagnostic.data
        || typeof diagnostic.data.reason !== 'string'
        || typeof diagnostic.data.source_path !== 'string'
    ) {
        return null;
    }
    // A local child result and an assembled host result describe one authored
    // transition. Keep mount paths out of this identity so the host result can
    // suppress its standalone counterpart without merging distinct mounts.
    return JSON.stringify([
        diagnostic.code,
        diagnostic.data.reason,
        diagnostic.data.source_path,
        diagnostic.range,
        diagnostic.data.forced_origin ?? null,
        diagnostic.data.combo_origin_ids ?? [],
    ]);
}

function isAssembledMountDiagnostic(diagnostic: FcstmDiagnostic): boolean {
    return diagnostic.code === 'W_UNREACHABLE_TRANSITION'
        && typeof diagnostic.data?.mount_path === 'string'
        && diagnostic.data.mount_path.length > 0;
}

export class FcstmDiagnosticsProvider {
    private readonly diagnosticCollection: vscode.DiagnosticCollection;
    private readonly documentVersions = new Map<string, number>();
    private readonly diagnosticContributions = new Map<string, Map<string, FcstmDiagnostic[]>>();
    private readonly diagnosticAuthorities = new Map<string, ReadonlySet<string>>();
    private debounceTimers = new Map<string, NodeJS.Timeout>();

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('fcstm');
    }

    register(context: vscode.ExtensionContext): void {
        context.subscriptions.push(this.diagnosticCollection);

        context.subscriptions.push(
            vscode.workspace.onDidOpenTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    this.updateDiagnostics(document);
                }
            })
        );

        context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    this.updateDiagnostics(document);
                }
            })
        );

        context.subscriptions.push(
            vscode.workspace.onDidChangeTextDocument(event => {
                if (event.document.languageId === 'fcstm') {
                    this.scheduleDiagnostics(event.document);
                }
            })
        );

        context.subscriptions.push(
            vscode.workspace.onDidCloseTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    const uri = document.uri.toString();
                    const previous = this.diagnosticContributions.get(uri);
                    this.diagnosticContributions.delete(uri);
                    const previousAuthorities = this.diagnosticAuthorities.get(uri);
                    this.diagnosticAuthorities.delete(uri);
                    this.documentVersions.delete(uri);
                    const targets = new Set(previous?.keys() || []);
                    for (const target of previousAuthorities || []) targets.add(target);
                    if (targets.size === 0) targets.add(uri);
                    this.publishDiagnosticTargets(targets);
                }
            })
        );

        vscode.workspace.textDocuments.forEach(document => {
            if (document.languageId === 'fcstm') {
                this.updateDiagnostics(document);
            }
        });
    }

    private scheduleDiagnostics(document: vscode.TextDocument): void {
        const uri = document.uri.toString();
        const existingTimer = this.debounceTimers.get(uri);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        const timer = setTimeout(() => {
            this.updateDiagnostics(document);
            this.debounceTimers.delete(uri);
        }, 500);

        this.debounceTimers.set(uri, timer);
    }

    private async updateDiagnostics(document: vscode.TextDocument): Promise<void> {
        const uri = document.uri.toString();
        const currentVersion = document.version;
        this.documentVersions.set(uri, currentVersion);

        try {
            const publications = await collectDocumentDiagnosticsByUri(document, uri);
            if (this.documentVersions.get(uri) !== currentVersion) {
                return;
            }

            const next = new Map<string, FcstmDiagnostic[]>(publications);
            const previous = this.diagnosticContributions.get(uri);
            const previousAuthorities = this.diagnosticAuthorities.get(uri);
            const nextAuthorities = new Set(
                (publications as DiagnosticPublications).authoritativeTargets || [],
            );
            const existingTargets = new Set(
                [...this.diagnosticContributions.values()]
                    .flatMap(contribution => [...contribution.keys()]),
            );
            const targets = new Set([
                ...(previous?.keys() || []),
                ...next.keys(),
                ...(previousAuthorities || []),
            ]);
            for (const target of nextAuthorities) {
                if (existingTargets.has(target)) targets.add(target);
            }
            this.diagnosticContributions.set(uri, next);
            this.diagnosticAuthorities.set(uri, nextAuthorities);
            this.publishDiagnosticTargets(targets);
        } catch (error) {
            console.error('Error updating diagnostics:', error);
        }
    }

    private publishDiagnosticTargets(targets: Iterable<string>): void {
        for (const targetUri of targets) {
            const diagnostics: vscode.Diagnostic[] = [];
            const seen = new Set<string>();
            const contributions = [...this.diagnosticContributions.entries()]
                .flatMap(([sourceUri, contribution]) => (contribution.get(targetUri) || [])
                    .map(diagnostic => ({sourceUri, diagnostic})));
            const authoritativeSources = new Set(
                [...this.diagnosticAuthorities.entries()]
                    .filter(([, authoritativeTargets]) => authoritativeTargets.has(targetUri))
                    .map(([sourceUri]) => sourceUri),
            );
            const assembledAuthoredKeys = new Set(
                contributions
                    .map(item => item.diagnostic)
                    .filter(isAssembledMountDiagnostic)
                    .map(unreachableTransitionAuthoredKey)
                    .filter((key): key is string => key !== null),
            );
            for (const {sourceUri, diagnostic} of contributions) {
                const authoredKey = unreachableTransitionAuthoredKey(diagnostic);
                if (
                    authoredKey !== null
                    && !isAssembledMountDiagnostic(diagnostic)
                    && (
                        assembledAuthoredKeys.has(authoredKey)
                        || [...authoritativeSources].some(authoritySource => authoritySource !== sourceUri)
                    )
                ) {
                    // An assembled result owns the imported target even
                    // when it has no positive topology warning.
                    continue;
                }
                const key = diagnosticContributionKey(diagnostic);
                if (seen.has(key)) continue;
                seen.add(key);
                diagnostics.push(toVscodeDiagnostic(diagnostic));
            }
            this.diagnosticCollection.set(vscode.Uri.parse(targetUri), diagnostics);
        }
    }

    dispose(): void {
        this.diagnosticCollection.dispose();
        this.debounceTimers.forEach(timer => clearTimeout(timer));
        this.debounceTimers.clear();
        this.diagnosticContributions.clear();
        this.diagnosticAuthorities.clear();
    }
}
