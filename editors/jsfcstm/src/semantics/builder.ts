import type {
    FcstmAstAction,
    FcstmAstChainPath,
    FcstmAstDocument,
    FcstmAstEventDefinition,
    FcstmAstForcedTransition,
    FcstmAstImportDefMapping,
    FcstmAstImportEventMapping,
    FcstmAstImportStatement,
    FcstmAstStateDefinition,
    FcstmAstStateStatement,
    FcstmAstTransition,
    FcstmAstVariableDefinition,
} from '../ast';
import {
    type FcstmExpandedForceTransition,
    type FcstmSemanticAction,
    type FcstmSemanticActionReference,
    type FcstmSemanticDocument,
    type FcstmSemanticEvent,
    type FcstmSemanticEventReference,
    type FcstmSemanticFile,
    type FcstmSemanticImport,
    type FcstmSemanticMachine,
    type FcstmSemanticModule,
    type FcstmSemanticState,
    type FcstmSemanticSummary,
    type FcstmSemanticTransition,
    type FcstmSemanticVariable,
    type FcstmSymbolIdentity,
} from './model';

function pathKey(path: string[]): string {
    return path.join('.');
}

function uniquePush(target: string[], value: string | undefined): void {
    if (value && !target.includes(value)) {
        target.push(value);
    }
}

function applyTemplate(template: string, original: string, captures: string[]): string {
    if (template === '*') {
        return original;
    }

    let result = template;
    captures.forEach((capture, index) => {
        result = result.replace(new RegExp(`\\$${index + 1}`, 'g'), capture);
    });
    return result;
}

function escapeRegex(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function applyImportDefMappings(
    names: string[],
    mappings: FcstmAstImportDefMapping[]
): string[] {
    const results: string[] = [];

    for (const name of names) {
        let mappedName = name;

        for (const mapping of mappings) {
            const selector = mapping.selector;
            let matched = false;
            let captures: string[] = [];

            if (selector.kind === 'importDefFallbackSelector') {
                matched = true;
            } else if (selector.kind === 'importDefExactSelector') {
                matched = selector.name === name;
            } else if (selector.kind === 'importDefSetSelector') {
                matched = selector.names.includes(name);
            } else if (selector.kind === 'importDefPatternSelector') {
                const regex = new RegExp(`^${escapeRegex(selector.pattern).replace(/\\\*/g, '(.*)')}$`);
                const match = regex.exec(name);
                matched = Boolean(match);
                captures = match ? match.slice(1) : [];
            }

            if (matched) {
                mappedName = applyTemplate(mapping.targetTemplate, name, captures);
                break;
            }
        }

        uniquePush(results, mappedName);
    }

    return results;
}

export function applyImportEventMappings(
    paths: string[],
    mappings: FcstmAstImportEventMapping[]
): string[] {
    const results: string[] = [];

    for (const eventPath of paths) {
        const mapping = mappings.find(item => item.sourceEvent.text === eventPath);
        uniquePush(results, mapping ? mapping.targetEvent.text : eventPath);
    }

    return results;
}

class SemanticBuilder {
    private readonly filePath: string;
    private readonly variables: FcstmSemanticVariable[] = [];
    private readonly states: FcstmSemanticState[] = [];
    private readonly events: FcstmSemanticEvent[] = [];
    private readonly transitions: FcstmSemanticTransition[] = [];
    private readonly actions: FcstmSemanticAction[] = [];
    private readonly imports: FcstmSemanticImport[] = [];
    private readonly statesByPath = new Map<string, FcstmSemanticState>();
    private readonly actionsByPath = new Map<string, FcstmSemanticAction>();
    private readonly eventsByQualifiedName = new Map<string, FcstmSemanticEvent>();
    private readonly importsByPath = new Map<string, FcstmSemanticImport>();
    private rootState: FcstmSemanticState | undefined;
    private nextId = 0;

    constructor(private readonly ast: FcstmAstDocument) {
        this.filePath = ast.filePath;
    }

    build(): FcstmSemanticDocument {
        const fileIdentity = this.createIdentity('file', this.filePath || '<memory>', []);
        const file: FcstmSemanticFile = {
            identity: fileIdentity,
            filePath: this.filePath,
            range: this.ast.range,
        };
        const module: FcstmSemanticModule = {
            identity: this.createIdentity('module', this.filePath || '<memory>', []),
            fileId: fileIdentity.id,
            filePath: this.filePath,
        };
        const machine: FcstmSemanticMachine = {
            identity: this.createIdentity('machine', this.ast.rootState?.name || '<machine>', []),
            moduleId: module.identity.id,
        };

        this.variables.push(...this.ast.variables.map(variable => this.buildVariable(variable)));
        if (this.ast.rootState) {
            this.rootState = this.buildState(this.ast.rootState, undefined);
            module.rootStateId = this.rootState.identity.id;
            machine.rootStateId = this.rootState.identity.id;
        }

        this.finalizeActions();
        this.finalizeTransitions();

        const summary = this.buildSummary();

        return {
            kind: 'semanticDocument',
            file,
            module,
            machine,
            ast: this.ast,
            variables: this.variables,
            states: this.states,
            events: this.events,
            transitions: this.transitions,
            actions: this.actions,
            imports: this.imports,
            summary,
            lookups: {
                statesByPath: Object.fromEntries(this.states.map(state => [pathKey(state.identity.path), state])),
                actionsByPath: Object.fromEntries(this.actionsByPath.entries()),
                eventsByQualifiedName: Object.fromEntries(this.eventsByQualifiedName.entries()),
                importsByPath: Object.fromEntries(this.importsByPath.entries()),
            },
        };
    }

    private createIdentity(
        kind: FcstmSymbolIdentity['kind'],
        name: string,
        path: string[]
    ): FcstmSymbolIdentity {
        const qualifiedName = path.length > 0 ? path.join('.') : name;
        this.nextId += 1;
        return {
            id: `${kind}:${this.filePath}:${qualifiedName || name}:${this.nextId}`,
            kind,
            name,
            qualifiedName: qualifiedName || name,
            path,
        };
    }

    private buildVariable(variable: FcstmAstVariableDefinition): FcstmSemanticVariable {
        return {
            identity: this.createIdentity('variable', variable.name, [variable.name]),
            name: variable.name,
            valueType: variable.valueType,
            initializer: variable.initializer,
            ast: variable,
            range: variable.range,
        };
    }

    private buildState(
        state: FcstmAstStateDefinition,
        parent: FcstmSemanticState | undefined
    ): FcstmSemanticState {
        const path = parent ? [...parent.identity.path, state.name] : [state.name];
        const semanticState: FcstmSemanticState = {
            identity: this.createIdentity('state', state.name, path),
            name: state.name,
            displayName: state.displayName,
            pseudo: state.pseudo,
            composite: state.composite,
            range: state.range,
            ast: state,
            parentStateId: parent?.identity.id,
            childStateIds: [],
        };

        this.states.push(semanticState);
        this.statesByPath.set(pathKey(path), semanticState);
        if (!parent && !this.rootState) {
            this.rootState = semanticState;
        }
        if (parent) {
            parent.childStateIds.push(semanticState.identity.id);
        }

        for (const statement of state.statements) {
            this.buildStateStatement(statement, semanticState);
        }

        return semanticState;
    }

    private buildStateStatement(
        statement: FcstmAstStateStatement,
        ownerState: FcstmSemanticState
    ): void {
        switch (statement.kind) {
            case 'stateDefinition':
                this.buildState(statement, ownerState);
                break;
            case 'eventDefinition':
                this.buildEvent(statement, ownerState, 'declared');
                break;
            case 'action':
                this.buildAction(statement, ownerState);
                break;
            case 'transition':
                this.buildTransition(statement, ownerState, false);
                break;
            case 'forcedTransition':
                this.buildTransition(statement, ownerState, true);
                break;
            case 'importStatement':
                this.buildImport(statement, ownerState);
                break;
            default:
                break;
        }
    }

    private buildEvent(
        event: FcstmAstEventDefinition,
        ownerState: FcstmSemanticState,
        origin: 'declared' | 'local' | 'chain' | 'absolute'
    ): FcstmSemanticEvent {
        const normalizedPath = [...ownerState.identity.path, event.name];
        const key = pathKey(normalizedPath);
        let semanticEvent = this.eventsByQualifiedName.get(key);

        if (!semanticEvent) {
            semanticEvent = {
                identity: this.createIdentity('event', event.name, normalizedPath),
                name: event.name,
                displayName: event.displayName,
                range: event.range,
                statePath: ownerState.identity.path,
                declared: origin === 'declared',
                origins: [origin],
                absolutePathText: this.isRootPath(ownerState.identity.path) ? `/${event.name}` : undefined,
                declarationAst: origin === 'declared' ? event : undefined,
            };
            this.events.push(semanticEvent);
            this.eventsByQualifiedName.set(key, semanticEvent);
        } else {
            semanticEvent.declared = semanticEvent.declared || origin === 'declared';
            semanticEvent.displayName = semanticEvent.displayName || event.displayName;
            uniquePush(semanticEvent.origins, origin);
            if (origin === 'declared') {
                semanticEvent.declarationAst = event;
            }
        }

        return semanticEvent;
    }

    private ensureImplicitEvent(
        ownerStatePath: string[],
        eventName: string,
        eventPathSegments: string[],
        origin: 'local' | 'chain' | 'absolute',
        range: FcstmSemanticEventReference['range']
    ): FcstmSemanticEventReference {
        const scopePath = origin === 'absolute'
            ? (this.rootState ? this.rootState.identity.path : ownerStatePath)
            : ownerStatePath;
        const normalizedPath = [...scopePath, ...eventPathSegments];
        const key = pathKey(normalizedPath);
        let semanticEvent = this.eventsByQualifiedName.get(key);

        if (!semanticEvent) {
            semanticEvent = {
                identity: this.createIdentity('event', eventName, normalizedPath),
                name: eventName,
                range,
                statePath: scopePath,
                declared: false,
                origins: [origin],
                absolutePathText: origin === 'absolute' || this.isRootPath(scopePath)
                    ? `/${eventPathSegments.join('.')}`
                    : undefined,
            };
            this.events.push(semanticEvent);
            this.eventsByQualifiedName.set(key, semanticEvent);
        } else {
            uniquePush(semanticEvent.origins, origin);
        }

        return {
            scope: origin,
            rawText: origin === 'local' ? eventName : `/${eventPathSegments.join('.')}`,
            range,
            eventId: semanticEvent.identity.id,
            normalizedPath,
            qualifiedName: semanticEvent.identity.qualifiedName,
            absolutePathText: semanticEvent.absolutePathText,
        };
    }

    private buildAction(
        action: FcstmAstAction,
        ownerState: FcstmSemanticState
    ): void {
        const fallbackName = `$${action.stage}:${this.actions.length}`;
        const identityPath = [...ownerState.identity.path, action.name || fallbackName];
        const semanticAction: FcstmSemanticAction = {
            identity: this.createIdentity('action', action.name || fallbackName, identityPath),
            stage: action.stage,
            aspect: action.aspect,
            isGlobalAspect: action.isGlobalAspect,
            mode: action.mode,
            name: action.name,
            range: action.range,
            ast: action,
            ownerStateId: ownerState.identity.id,
            ownerStatePath: ownerState.identity.path,
            operationsText: action.operations?.text,
            ref: action.refPath ? {
                rawPath: action.refPath.text,
                range: action.refPath.range,
                resolved: false,
            } : undefined,
            doc: action.doc,
        };

        this.actions.push(semanticAction);
        if (action.name) {
            this.actionsByPath.set(pathKey(identityPath), semanticAction);
        }
    }

    private buildTransition(
        transition: FcstmAstTransition | FcstmAstForcedTransition,
        ownerState: FcstmSemanticState,
        forced: boolean
    ): void {
        const semanticTransition: FcstmSemanticTransition = {
            identity: this.createIdentity(
                'transition',
                `${ownerState.name}:${transition.text}`,
                [...ownerState.identity.path, `$transition:${this.transitions.length}`]
            ),
            transitionKind: forced ? transition.transitionKind : transition.transitionKind,
            forced,
            range: transition.range,
            ast: transition,
            ownerStateId: ownerState.identity.id,
            ownerStatePath: ownerState.identity.path,
            sourceStateName: transition.sourceStateName,
            targetStateName: transition.targetStateName,
            sourceKind: transition.sourceKind,
            targetKind: transition.targetKind,
            guard: transition.guard,
            effectText: transition.effect?.text,
            expandedTransitions: [],
        };

        if (transition.trigger) {
            if (transition.trigger.kind === 'localTrigger') {
                const sourceState = this.resolveStateReference(ownerState.identity.path, transition.sourceStateName);
                const normalizedOwnerPath = sourceState?.identity.path || ownerState.identity.path;
                semanticTransition.trigger = this.ensureImplicitEvent(
                    normalizedOwnerPath,
                    transition.trigger.eventName,
                    [transition.trigger.eventName],
                    'local',
                    transition.trigger.range
                );
            } else {
                const triggerPath = transition.trigger.eventPath;
                semanticTransition.trigger = this.ensureImplicitEvent(
                    ownerState.identity.path,
                    triggerPath.segments[triggerPath.segments.length - 1] || triggerPath.text,
                    triggerPath.segments,
                    triggerPath.isAbsolute ? 'absolute' : 'chain',
                    transition.trigger.range
                );
                semanticTransition.trigger.rawText = triggerPath.text;
            }
        }

        this.transitions.push(semanticTransition);
    }

    private buildImport(
        importStatement: FcstmAstImportStatement,
        ownerState: FcstmSemanticState
    ): void {
        const sourcePath = importStatement.sourcePath;
        const alias = importStatement.alias;
        const semanticImport: FcstmSemanticImport = {
            identity: this.createIdentity('import', alias, [...ownerState.identity.path, alias]),
            range: importStatement.range,
            pathRange: importStatement.pathRange,
            aliasRange: importStatement.aliasRange,
            ast: importStatement,
            ownerStateId: ownerState.identity.id,
            ownerStatePath: ownerState.identity.path,
            sourcePath,
            alias,
            displayName: importStatement.displayName,
            mountedStatePath: [...ownerState.identity.path, alias],
            defMappings: importStatement.mappings.filter(item => item.kind === 'importDefMapping') as FcstmAstImportDefMapping[],
            eventMappings: importStatement.mappings.filter(item => item.kind === 'importEventMapping') as FcstmAstImportEventMapping[],
            exists: false,
            missing: false,
            sourceVariables: [],
            sourceAbsoluteEvents: [],
            mappedVariables: [],
            mappedAbsoluteEvents: [],
        };

        this.imports.push(semanticImport);
        this.importsByPath.set(pathKey([...ownerState.identity.path, alias]), semanticImport);
    }

    private finalizeActions(): void {
        for (const action of this.actions) {
            if (!action.ref || !action.ast.refPath) {
                continue;
            }

            const resolved = this.resolveActionReference(action.ownerStatePath, action.ast.refPath);
            if (resolved) {
                action.ref.resolved = true;
                action.ref.targetActionId = resolved.identity.id;
                action.ref.targetQualifiedName = resolved.identity.qualifiedName;
            }
        }
    }

    private finalizeTransitions(): void {
        for (const transition of this.transitions) {
            if (transition.sourceKind === 'state' && transition.sourceStateName) {
                const sourceState = this.resolveStateReference(transition.ownerStatePath, transition.sourceStateName);
                transition.sourceStateId = sourceState?.identity.id;
                transition.sourceStatePath = sourceState?.identity.path;
            }

            if (transition.targetKind === 'state' && transition.targetStateName) {
                const targetState = this.resolveStateReference(transition.ownerStatePath, transition.targetStateName);
                transition.targetStateId = targetState?.identity.id;
                transition.targetStatePath = targetState?.identity.path;
            }

            if (transition.forced) {
                transition.expandedTransitions = this.expandForcedTransition(transition);
            }
        }
    }

    private resolveStateReference(
        ownerStatePath: string[],
        stateName?: string
    ): FcstmSemanticState | undefined {
        if (!stateName) {
            return undefined;
        }

        if (this.rootState && this.rootState.name === stateName) {
            return this.rootState;
        }

        for (let length = ownerStatePath.length; length >= 1; length--) {
            const candidatePath = [...ownerStatePath.slice(0, length), stateName];
            const candidate = this.statesByPath.get(pathKey(candidatePath));
            if (candidate) {
                return candidate;
            }
        }

        const globalMatches = this.states.filter(state => state.name === stateName);
        return globalMatches.length === 1 ? globalMatches[0] : undefined;
    }

    private resolveActionReference(
        ownerStatePath: string[],
        refPath: FcstmAstChainPath
    ): FcstmSemanticAction | undefined {
        const segments = refPath.segments;
        if (segments.length === 0) {
            return undefined;
        }

        const actionName = segments[segments.length - 1];
        const stateSegments = segments.slice(0, -1);

        if (refPath.isAbsolute) {
            const absolutePath = this.rootState
                ? [...this.rootState.identity.path, ...stateSegments, actionName]
                : [...stateSegments, actionName];
            return this.actionsByPath.get(pathKey(absolutePath));
        }

        for (let length = ownerStatePath.length; length >= 1; length--) {
            const candidatePath = [...ownerStatePath.slice(0, length), ...stateSegments, actionName];
            const candidate = this.actionsByPath.get(pathKey(candidatePath));
            if (candidate) {
                return candidate;
            }
        }

        const namedMatches = this.actions.filter(action => action.name === actionName);
        return namedMatches.length === 1 ? namedMatches[0] : undefined;
    }

    private expandForcedTransition(
        transition: FcstmSemanticTransition
    ): FcstmExpandedForceTransition[] {
        const roots = transition.sourceKind === 'all'
            ? this.getDirectChildStates(transition.ownerStatePath)
            : transition.sourceStatePath
                ? [this.statesByPath.get(pathKey(transition.sourceStatePath))]
                : [];
        const expanded: FcstmExpandedForceTransition[] = [];

        for (const root of roots.filter(Boolean) as FcstmSemanticState[]) {
            expanded.push({
                sourceStateId: root.identity.id,
                sourceStatePath: root.identity.path,
                mode: 'direct',
                targetKind: transition.targetKind,
                targetStateId: transition.targetStateId,
                targetStatePath: transition.targetStatePath,
            });

            if (root.childStateIds.length === 0) {
                continue;
            }

            for (const descendant of this.getLeafDescendants(root)) {
                expanded.push({
                    sourceStateId: descendant.identity.id,
                    sourceStatePath: descendant.identity.path,
                    mode: 'exitToParent',
                    targetKind: 'exit',
                    targetStateId: root.identity.id,
                    targetStatePath: root.identity.path,
                });
            }
        }

        return expanded;
    }

    private getLeafDescendants(root: FcstmSemanticState): FcstmSemanticState[] {
        const descendants: FcstmSemanticState[] = [];

        for (const childId of root.childStateIds) {
            const child = this.states.find(state => state.identity.id === childId);
            if (!child) {
                continue;
            }
            if (child.childStateIds.length === 0) {
                descendants.push(child);
            } else {
                descendants.push(...this.getLeafDescendants(child));
            }
        }

        return descendants;
    }

    private getDirectChildStates(ownerStatePath: string[]): FcstmSemanticState[] {
        const ownerKey = pathKey(ownerStatePath);
        return this.states.filter(state => pathKey(state.identity.path.slice(0, -1)) === ownerKey);
    }

    private isRootPath(path: string[]): boolean {
        return Boolean(this.rootState && pathKey(path) === pathKey(this.rootState.identity.path));
    }

    private buildSummary(): FcstmSemanticSummary {
        const rootStateName = this.rootState?.name;
        const explicitVariables = this.variables.map(variable => variable.name);
        const absoluteEvents: string[] = [];

        for (const event of this.events) {
            uniquePush(absoluteEvents, event.absolutePathText);
        }

        return {
            rootStateName,
            explicitVariables,
            absoluteEvents,
        };
    }
}

export function buildSemanticDocument(
    ast: FcstmAstDocument | null
): FcstmSemanticDocument | null {
    if (!ast) {
        return null;
    }

    return new SemanticBuilder(ast).build();
}
