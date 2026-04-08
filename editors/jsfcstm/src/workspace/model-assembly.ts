import type {
    FcstmAstAction,
    FcstmAstChainPath,
    FcstmAstDocument,
    FcstmAstExpression,
    FcstmAstImportDefMapping,
    FcstmAstImportDefSelector,
    FcstmAstImportEventMapping,
    FcstmAstImportStatement,
    FcstmAstOperationStatement,
    FcstmAstStateDefinition,
    FcstmAstTransition,
    FcstmAstForcedTransition,
    FcstmAstVariableDefinition,
} from '../ast';
import {
    buildStateMachineModelFromAst,
    type StateMachine as FcstmStateMachineModel,
} from '../model';
import type {FcstmSemanticDocument, FcstmSemanticImport} from '../semantics';

interface WorkspaceAssemblyNode {
    filePath: string;
    ast: FcstmAstDocument | null;
    semantic: FcstmSemanticDocument | null;
}

interface WorkspaceAssemblySnapshotLike {
    rootFile: string;
    nodes: Record<string, WorkspaceAssemblyNode>;
}

interface ResolvedImportEventMapping {
    sourcePath: string[];
    targetStatePath: string[];
    targetEventName: string;
    targetEventIdPath: string[];
    extraName?: string;
}

interface PendingEventRegistration {
    targetStatePath: string[];
    targetEventName: string;
    mappingExtraName?: string;
    sourceExtraName?: string;
    sourcePath: string[];
}

const IMPORT_KEY_SEPARATOR = '\u0000';

function pathKey(path: string[]): string {
    return path.join(IMPORT_KEY_SEPARATOR);
}

function importLookupKey(ownerStatePath: string[], alias: string): string {
    return `${pathKey(ownerStatePath)}${IMPORT_KEY_SEPARATOR}${alias}`;
}

function cloneAstValue<T>(value: T, cache = new Map<object, unknown>()): T {
    if (Array.isArray(value)) {
        if (cache.has(value as unknown as object)) {
            return cache.get(value as unknown as object) as T;
        }

        const clone: unknown[] = [];
        cache.set(value as unknown as object, clone);
        for (const item of value) {
            clone.push(cloneAstValue(item, cache));
        }
        return clone as T;
    }

    if (value && typeof value === 'object') {
        if (cache.has(value as object)) {
            return cache.get(value as object) as T;
        }

        const clone: Record<string, unknown> = {};
        cache.set(value as object, clone);
        for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
            clone[key] = cloneAstValue(item, cache);
        }
        return clone as T;
    }

    return value;
}

function chainPathText(path: string[], isAbsolute: boolean): string {
    return `${isAbsolute ? '/' : ''}${path.join('.')}`;
}

function buildImportLookup(imports: FcstmSemanticImport[]): Map<string, FcstmSemanticImport> {
    const lookup = new Map<string, FcstmSemanticImport>();
    for (const item of imports) {
        lookup.set(importLookupKey(item.ownerStatePath, item.alias), item);
    }
    return lookup;
}

function collectEventExtraNames(
    node: FcstmAstStateDefinition,
    currentPath: string[],
    output: Map<string, string | undefined>
): void {
    const currentStatePath = [...currentPath, node.name];
    for (const event of node.events) {
        const localKey = pathKey([node.name, event.name]);
        if (!output.has(localKey)) {
            output.set(localKey, event.extraName);
        }
        output.set(pathKey([...currentStatePath.slice(1), event.name]), event.extraName);

        const bareKey = pathKey([event.name]);
        if (!output.has(bareKey)) {
            output.set(bareKey, event.extraName);
        }
    }

    for (const substate of node.substates) {
        collectEventExtraNames(substate, currentStatePath, output);
    }
}

function lookupSourceEventExtraName(
    sourcePath: string[],
    sourceEventNames: Map<string, string | undefined>
): string | undefined {
    return sourceEventNames.get(pathKey(sourcePath));
}

function ensureStatePathExists(
    root: FcstmAstStateDefinition,
    statePath: string[]
): FcstmAstStateDefinition {
    if (statePath.length === 0) {
        throw new Error('Invalid empty host state path for event mapping.');
    }
    if (root.name !== statePath[0]) {
        throw new Error(
            `Invalid host root path for event mapping: expected root ${JSON.stringify(root.name)}, got ${JSON.stringify(statePath[0])}.`
        );
    }

    let state = root;
    for (const segment of statePath.slice(1)) {
        const nextState = state.substates.find(item => item.name === segment);
        if (!nextState) {
            throw new Error(
                `Event mapping target state ${JSON.stringify(`/${statePath.join('.')}`)} does not exist in host model.`
            );
        }
        state = nextState;
    }

    return state;
}

function rewriteExpressionVariables(
    expression: FcstmAstExpression,
    sourceToTarget: Record<string, string>
): void {
    switch (expression.expressionKind) {
        case 'identifier':
            if (expression.name in sourceToTarget) {
                expression.name = sourceToTarget[expression.name];
            }
            break;
        case 'parenthesized':
            rewriteExpressionVariables(expression.expression, sourceToTarget);
            break;
        case 'unary':
            rewriteExpressionVariables(expression.operand, sourceToTarget);
            break;
        case 'binary':
            rewriteExpressionVariables(expression.left, sourceToTarget);
            rewriteExpressionVariables(expression.right, sourceToTarget);
            break;
        case 'conditional':
            rewriteExpressionVariables(expression.condition, sourceToTarget);
            rewriteExpressionVariables(expression.whenTrue, sourceToTarget);
            rewriteExpressionVariables(expression.whenFalse, sourceToTarget);
            break;
        case 'function':
            rewriteExpressionVariables(expression.argument, sourceToTarget);
            break;
        default:
            break;
    }
}

function rewriteOperationStatementVariables(
    statement: FcstmAstOperationStatement,
    sourceToTarget: Record<string, string>
): void {
    if (statement.kind === 'assignmentStatement') {
        if (statement.name in sourceToTarget) {
            statement.name = sourceToTarget[statement.name];
            statement.targetName = sourceToTarget[statement.targetName] || statement.name;
        }
        rewriteExpressionVariables(statement.expression, sourceToTarget);
        return;
    }

    if (statement.kind === 'ifStatement') {
        for (const branch of statement.branches) {
            if (branch.condition) {
                rewriteExpressionVariables(branch.condition, sourceToTarget);
            }
            for (const item of branch.statements) {
                rewriteOperationStatementVariables(item, sourceToTarget);
            }
        }
    }
}

function rewriteOperationBlockVariables(
    statements: FcstmAstOperationStatement[],
    sourceToTarget: Record<string, string>
): void {
    for (const item of statements) {
        rewriteOperationStatementVariables(item, sourceToTarget);
    }
}

function rewriteStateVariableReferences(
    node: FcstmAstStateDefinition,
    sourceToTarget: Record<string, string>
): void {
    for (const transition of node.transitions) {
        if (transition.guard) {
            rewriteExpressionVariables(transition.guard, sourceToTarget);
        }
        rewriteOperationBlockVariables(transition.postOperations, sourceToTarget);
    }

    for (const transition of node.forceTransitions) {
        if (transition.guard) {
            rewriteExpressionVariables(transition.guard, sourceToTarget);
        }
    }

    for (const item of node.enters) {
        if (item.mode === 'operations' && item.operations) {
            rewriteOperationBlockVariables(item.operations, sourceToTarget);
        }
    }
    for (const item of node.durings) {
        if (item.mode === 'operations' && item.operations) {
            rewriteOperationBlockVariables(item.operations, sourceToTarget);
        }
    }
    for (const item of node.exits) {
        if (item.mode === 'operations' && item.operations) {
            rewriteOperationBlockVariables(item.operations, sourceToTarget);
        }
    }
    for (const item of node.duringAspects) {
        if (item.mode === 'operations' && item.operations) {
            rewriteOperationBlockVariables(item.operations, sourceToTarget);
        }
    }

    for (const substate of node.substates) {
        rewriteStateVariableReferences(substate, sourceToTarget);
    }
}

function matchPatternSelector(pattern: string, sourceName: string): string[] | null {
    const parts = pattern.split('*');
    const regex = new RegExp(`^${parts.map(part => part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('(.*?)')}$`);
    const match = regex.exec(sourceName);
    return match ? match.slice(1) : null;
}

function mappingPlaceholderValue(
    sourceName: string,
    captures: string[],
    index: number,
    template: string,
    importItem: FcstmAstImportStatement,
    ownerStatePath: string[]
): string {
    if (index === 0) {
        return sourceName;
    }
    if (index >= 1 && index <= captures.length) {
        return captures[index - 1];
    }

    throw new Error(
        `Invalid variable mapping template ${JSON.stringify(template)} in import ${JSON.stringify(importItem.alias)} under state ${JSON.stringify(ownerStatePath.join('.'))}: placeholder $${index} is out of range for source variable ${JSON.stringify(sourceName)}.`
    );
}

function renderTargetTemplate(
    template: string,
    sourceName: string,
    captures: string[],
    importItem: FcstmAstImportStatement,
    ownerStatePath: string[]
): string {
    let rendered = '';
    let index = 0;

    while (index < template.length) {
        if (template[index] === '$') {
            if (index + 1 < template.length && template[index + 1] === '{') {
                const endIndex = template.indexOf('}', index + 2);
                if (endIndex < 0) {
                    throw new Error(
                        `Invalid variable mapping template ${JSON.stringify(template)} in import ${JSON.stringify(importItem.alias)}: missing closing '}'.`
                    );
                }

                const rawIndex = template.slice(index + 2, endIndex);
                if (!/^\d+$/.test(rawIndex)) {
                    throw new Error(
                        `Invalid variable mapping template ${JSON.stringify(template)} in import ${JSON.stringify(importItem.alias)}: placeholder index ${JSON.stringify(rawIndex)} is not numeric.`
                    );
                }

                rendered += mappingPlaceholderValue(
                    sourceName,
                    captures,
                    Number(rawIndex),
                    template,
                    importItem,
                    ownerStatePath
                );
                index = endIndex + 1;
                continue;
            }

            if (index + 1 < template.length && /\d/.test(template[index + 1])) {
                rendered += mappingPlaceholderValue(
                    sourceName,
                    captures,
                    Number(template[index + 1]),
                    template,
                    importItem,
                    ownerStatePath
                );
                index += 2;
                continue;
            }
        }

        if (template[index] === '*') {
            if (captures.length > 1) {
                throw new Error(
                    `Invalid variable mapping template ${JSON.stringify(template)} in import ${JSON.stringify(importItem.alias)}: bare '*' is ambiguous when the source selector has multiple capture groups.`
                );
            }
            rendered += captures.length === 0 ? sourceName : captures[0];
            index += 1;
            continue;
        }

        rendered += template[index];
        index += 1;
    }

    return rendered;
}

function resolveImportVariableTarget(
    sourceName: string,
    mappings: FcstmAstImportDefMapping[],
    importItem: FcstmAstImportStatement,
    ownerStatePath: string[]
): string {
    const exactRules: FcstmAstImportDefMapping[] = [];
    const setRules: FcstmAstImportDefMapping[] = [];
    const patternRules: FcstmAstImportDefMapping[] = [];
    const fallbackRules: FcstmAstImportDefMapping[] = [];
    const seenExactNames = new Map<string, FcstmAstImportDefMapping>();
    const seenSetNames = new Map<string, FcstmAstImportDefMapping>();

    for (const mapping of mappings) {
        const selector = mapping.selector as FcstmAstImportDefSelector;
        switch (selector.kind) {
            case 'importDefExactSelector':
                if (seenExactNames.has(selector.name)) {
                    throw new Error(
                        `Variable mapping conflict: duplicated exact selector ${JSON.stringify(selector.name)} in import ${JSON.stringify(importItem.alias)}.`
                    );
                }
                seenExactNames.set(selector.name, mapping);
                exactRules.push(mapping);
                break;
            case 'importDefSetSelector': {
                const localNames = new Set<string>();
                for (const item of selector.names) {
                    if (localNames.has(item)) {
                        throw new Error(
                            `Variable mapping conflict: duplicated selector name ${JSON.stringify(item)} inside set rule in import ${JSON.stringify(importItem.alias)}.`
                        );
                    }
                    if (seenSetNames.has(item)) {
                        throw new Error(
                            `Variable mapping conflict: selector name ${JSON.stringify(item)} appears in multiple set rules in import ${JSON.stringify(importItem.alias)}.`
                        );
                    }
                    localNames.add(item);
                    seenSetNames.set(item, mapping);
                }
                setRules.push(mapping);
                break;
            }
            case 'importDefPatternSelector':
                patternRules.push(mapping);
                break;
            case 'importDefFallbackSelector':
                fallbackRules.push(mapping);
                break;
            default:
                throw new Error(`Unknown import def selector: ${JSON.stringify((selector as {kind?: string}).kind)}.`);
        }
    }

    if (fallbackRules.length > 1) {
        throw new Error(
            `Variable mapping conflict: multiple fallback rules found in import ${JSON.stringify(importItem.alias)}.`
        );
    }

    const exactMatch = exactRules.find(item => item.selector.kind === 'importDefExactSelector' && item.selector.name === sourceName);
    if (exactMatch) {
        return renderTargetTemplate(
            exactMatch.targetTemplate,
            sourceName,
            [],
            importItem,
            ownerStatePath
        );
    }

    const setMatches = setRules.filter(
        item => item.selector.kind === 'importDefSetSelector' && item.selector.names.includes(sourceName)
    );
    if (setMatches.length > 1) {
        throw new Error(
            `Variable mapping conflict: selector name ${JSON.stringify(sourceName)} matches multiple set rules in import ${JSON.stringify(importItem.alias)}.`
        );
    }
    if (setMatches.length === 1) {
        return renderTargetTemplate(
            setMatches[0].targetTemplate,
            sourceName,
            [],
            importItem,
            ownerStatePath
        );
    }

    const patternMatches = patternRules
        .map(item => ({
            item,
            captures: item.selector.kind === 'importDefPatternSelector'
                ? matchPatternSelector(item.selector.pattern, sourceName)
                : null,
        }))
        .filter(item => item.captures !== null) as Array<{item: FcstmAstImportDefMapping; captures: string[]}>;
    if (patternMatches.length > 1) {
        throw new Error(
            `Variable mapping conflict: source variable ${JSON.stringify(sourceName)} matches multiple pattern rules in import ${JSON.stringify(importItem.alias)}.`
        );
    }
    if (patternMatches.length === 1) {
        return renderTargetTemplate(
            patternMatches[0].item.targetTemplate,
            sourceName,
            patternMatches[0].captures,
            importItem,
            ownerStatePath
        );
    }

    if (fallbackRules.length === 1) {
        return renderTargetTemplate(
            fallbackRules[0].targetTemplate,
            sourceName,
            [],
            importItem,
            ownerStatePath
        );
    }

    throw new Error(
        `Variable mapping conflict: source variable ${JSON.stringify(sourceName)} in import ${JSON.stringify(importItem.alias)} under state ${JSON.stringify(ownerStatePath.join('.'))} is not matched by any def mapping rule.`
    );
}

function applyImportDefMappings(
    program: FcstmAstDocument,
    importItem: FcstmAstImportStatement,
    ownerStatePath: string[]
): void {
    let defMappings = importItem.mappings.filter(
        item => item.kind === 'importDefMapping'
    ) as FcstmAstImportDefMapping[];
    if (defMappings.length === 0) {
        defMappings = [{
            kind: 'importDefMapping',
            pyNodeType: 'ImportDefMapping',
            range: importItem.range,
            text: `def * -> ${importItem.alias}_*;`,
            selector: {
                kind: 'importDefFallbackSelector',
                pyNodeType: 'ImportDefFallbackSelector',
                range: importItem.range,
                text: '*',
            },
            targetTemplate: `${importItem.alias}_*`,
            targetTemplateNode: {
                kind: 'importDefTargetTemplate',
                pyNodeType: 'ImportDefTargetTemplate',
                range: importItem.range,
                text: `${importItem.alias}_*`,
                template: `${importItem.alias}_*`,
            },
            target_template: {
                kind: 'importDefTargetTemplate',
                pyNodeType: 'ImportDefTargetTemplate',
                range: importItem.range,
                text: `${importItem.alias}_*`,
                template: `${importItem.alias}_*`,
            },
        }];
    }

    if (program.definitions.length === 0) {
        return;
    }

    const sourceToTarget: Record<string, string> = {};
    const targetToSource: Record<string, string> = {};

    for (const definition of program.definitions) {
        const targetName = resolveImportVariableTarget(
            definition.name,
            defMappings,
            importItem,
            ownerStatePath
        );
        if (targetToSource[targetName] && targetToSource[targetName] !== definition.name) {
            throw new Error(
                `Variable mapping conflict: import ${JSON.stringify(importItem.alias)} maps multiple source variables to the same target variable ${JSON.stringify(targetName)}.`
            );
        }
        sourceToTarget[definition.name] = targetName;
        targetToSource[targetName] = definition.name;
    }

    for (const definition of program.definitions) {
        rewriteExpressionVariables(definition.initializer, sourceToTarget);
        definition.name = sourceToTarget[definition.name];
    }

    if (program.rootState) {
        rewriteStateVariableReferences(program.rootState, sourceToTarget);
    }
}

function mergeImportedDefinitions(
    hostProgram: FcstmAstDocument,
    importedProgram: FcstmAstDocument,
    hostExplicitDefNames: Set<string>
): void {
    const existingDefinitions = new Map<string, FcstmAstVariableDefinition>(
        hostProgram.definitions.map(item => [item.name, item])
    );

    for (const definition of importedProgram.definitions) {
        const existing = existingDefinitions.get(definition.name);
        if (!existing) {
            hostProgram.definitions.push(definition);
            existingDefinitions.set(definition.name, definition);
            continue;
        }

        if (existing.type !== definition.type) {
            if (hostExplicitDefNames.has(definition.name)) {
                throw new Error(
                    `Variable mapping conflict: target variable ${JSON.stringify(definition.name)} already exists in host model as type ${JSON.stringify(existing.type)}, cannot bind imported type ${JSON.stringify(definition.type)}.`
                );
            }
            throw new Error(
                `Variable mapping conflict: target variable ${JSON.stringify(definition.name)} receives incompatible imported types ${JSON.stringify(existing.type)} and ${JSON.stringify(definition.type)}.`
            );
        }

        if (hostExplicitDefNames.has(definition.name)) {
            continue;
        }

        if (JSON.stringify(existing.initializer) !== JSON.stringify(definition.initializer)) {
            throw new Error(
                `Variable mapping conflict: target variable ${JSON.stringify(definition.name)} has conflicting initial values.`
            );
        }
    }

    importedProgram.definitions.length = 0;
}

function resolveImportEventTargetPath(
    targetEvent: FcstmAstChainPath,
    ownerStatePath: string[]
): {targetStatePath: string[]; targetEventName: string; targetEventIdPath: string[]} {
    if (targetEvent.isAbsolute) {
        if (targetEvent.path.length < 1) {
            throw new Error('Invalid empty absolute target event path.');
        }
        return {
            targetStatePath: [ownerStatePath[0], ...targetEvent.path.slice(0, -1)],
            targetEventName: targetEvent.path[targetEvent.path.length - 1],
            targetEventIdPath: [...targetEvent.path],
        };
    }

    if (targetEvent.path.length < 1) {
        throw new Error('Invalid empty relative target event path.');
    }

    return {
        targetStatePath: [...ownerStatePath, ...targetEvent.path.slice(0, -1)],
        targetEventName: targetEvent.path[targetEvent.path.length - 1],
        targetEventIdPath: [...ownerStatePath.slice(1), ...targetEvent.path],
    };
}

function resolveImportEventMappings(
    importItem: FcstmAstImportStatement,
    ownerStatePath: string[]
): Map<string, ResolvedImportEventMapping> {
    const eventMappings = importItem.mappings.filter(
        item => item.kind === 'importEventMapping'
    ) as FcstmAstImportEventMapping[];
    const resolved = new Map<string, ResolvedImportEventMapping>();
    const targetToSource = new Map<string, string>();

    for (const mapping of eventMappings) {
        if (!mapping.sourceEvent.isAbsolute) {
            throw new Error(
                `Invalid event mapping in import ${JSON.stringify(importItem.alias)} under state ${JSON.stringify(ownerStatePath.join('.'))}: source event ${mapping.sourceEvent.text} must be a module-absolute path.`
            );
        }

        const sourcePath = [...mapping.sourceEvent.path];
        const target = resolveImportEventTargetPath(mapping.targetEvent, ownerStatePath);
        const sourceKey = pathKey(sourcePath);
        if (resolved.has(sourceKey)) {
            throw new Error(
                `Event mapping conflict: source event ${JSON.stringify(`/${sourcePath.join('.')}`)} appears multiple times in import ${JSON.stringify(importItem.alias)}.`
            );
        }

        const targetKey = pathKey([...target.targetStatePath, target.targetEventName]);
        if (targetToSource.has(targetKey) && targetToSource.get(targetKey) !== sourceKey) {
            throw new Error(
                `Event mapping conflict: import ${JSON.stringify(importItem.alias)} maps multiple module events to the same host event ${JSON.stringify(`/${[...target.targetStatePath, target.targetEventName].join('.')}`)}.`
            );
        }

        resolved.set(sourceKey, {
            sourcePath,
            targetStatePath: target.targetStatePath,
            targetEventName: target.targetEventName,
            targetEventIdPath: target.targetEventIdPath,
            extraName: mapping.extraName,
        });
        targetToSource.set(targetKey, sourceKey);
    }

    return resolved;
}

function rewriteTransitionEventId(
    transition: FcstmAstTransition | FcstmAstForcedTransition,
    currentScopePath: string[],
    sourceEventNames: Map<string, string | undefined>,
    resolvedEventMappings: Map<string, ResolvedImportEventMapping>,
    pendingRegistrations: PendingEventRegistration[]
): void {
    if (!transition.eventId) {
        return;
    }

    const sourcePath = transition.eventId.isAbsolute
        ? [...transition.eventId.path]
        : [...currentScopePath, ...transition.eventId.path];
    const sourceExtraName = lookupSourceEventExtraName(sourcePath, sourceEventNames);
    const mapping = resolvedEventMappings.get(pathKey(sourcePath));

    if (mapping) {
        transition.eventId.isAbsolute = true;
        transition.eventId.is_absolute = true;
        transition.eventId.path = [...mapping.targetEventIdPath];
        transition.eventId.segments = [...mapping.targetEventIdPath];
        transition.eventId.text = chainPathText(mapping.targetEventIdPath, true);
        pendingRegistrations.push({
            targetStatePath: [...mapping.targetStatePath],
            targetEventName: mapping.targetEventName,
            mappingExtraName: mapping.extraName,
            sourceExtraName,
            sourcePath,
        });
    } else if (transition.eventId.isAbsolute) {
        transition.eventId.path = [...currentScopePath, ...transition.eventId.path];
        transition.eventId.segments = [...transition.eventId.path];
        transition.eventId.text = chainPathText(transition.eventId.path, true);
    }
}

function rewriteImportedStateEventPaths(
    node: FcstmAstStateDefinition,
    currentPath: string[],
    sourceEventNames: Map<string, string | undefined>,
    resolvedEventMappings: Map<string, ResolvedImportEventMapping>,
    pendingRegistrations: PendingEventRegistration[]
): void {
    const currentStatePath = [...currentPath, node.name];
    const currentScopePath = currentStatePath.slice(1);

    for (const transition of node.transitions) {
        rewriteTransitionEventId(
            transition,
            currentScopePath,
            sourceEventNames,
            resolvedEventMappings,
            pendingRegistrations
        );
    }

    for (const transition of node.forceTransitions) {
        rewriteTransitionEventId(
            transition,
            currentScopePath,
            sourceEventNames,
            resolvedEventMappings,
            pendingRegistrations
        );
    }

    for (const substate of node.substates) {
        rewriteImportedStateEventPaths(
            substate,
            currentStatePath,
            sourceEventNames,
            resolvedEventMappings,
            pendingRegistrations
        );
    }
}

function pruneMappedSourceEventDefinitions(
    node: FcstmAstStateDefinition,
    currentPath: string[],
    resolvedEventMappings: Map<string, ResolvedImportEventMapping>
): void {
    const currentStatePath = [...currentPath, node.name];
    const currentScopePath = currentStatePath.slice(1);
    node.events = node.events.filter(
        item => !resolvedEventMappings.has(pathKey([...currentScopePath, item.name]))
    );

    for (const substate of node.substates) {
        pruneMappedSourceEventDefinitions(substate, currentStatePath, resolvedEventMappings);
    }
}

function validatePendingEventRegistrations(
    registrations: PendingEventRegistration[],
    importItem: FcstmAstImportStatement,
    ownerStatePath: string[]
): void {
    const byTarget = new Map<string, PendingEventRegistration>();
    for (const item of registrations) {
        const targetKey = pathKey([...item.targetStatePath, item.targetEventName]);
        const existing = byTarget.get(targetKey);
        if (!existing) {
            byTarget.set(targetKey, item);
            continue;
        }

        if (
            item.mappingExtraName !== undefined
            && existing.mappingExtraName !== undefined
            && item.mappingExtraName !== existing.mappingExtraName
        ) {
            throw new Error(
                `Event mapping conflict: host event ${JSON.stringify(`/${[...item.targetStatePath, item.targetEventName].join('.')}`)} receives conflicting display names ${JSON.stringify(existing.mappingExtraName)} and ${JSON.stringify(item.mappingExtraName)} in import ${JSON.stringify(importItem.alias)} under state ${JSON.stringify(ownerStatePath.join('.'))}.`
            );
        }
    }
}

function synthesizeHostEventsForImport(
    hostRoot: FcstmAstStateDefinition,
    registrations: PendingEventRegistration[]
): void {
    for (const item of registrations) {
        const ownerState = ensureStatePathExists(hostRoot, item.targetStatePath);
        const existingEvent = ownerState.events.find(event => event.name === item.targetEventName);
        const finalExtraName = item.mappingExtraName
            ?? existingEvent?.extraName
            ?? item.sourceExtraName;

        if (!existingEvent) {
            ownerState.events.push({
                kind: 'eventDefinition',
                pyNodeType: 'EventDefinition',
                range: ownerState.range,
                text: `event ${item.targetEventName};`,
                name: item.targetEventName,
                displayName: finalExtraName,
                extraName: finalExtraName,
                extra_name: finalExtraName,
            });
            continue;
        }

        if (
            item.mappingExtraName !== undefined
            && existingEvent.extraName !== undefined
            && existingEvent.extraName !== item.mappingExtraName
        ) {
            throw new Error(
                `Event mapping conflict: host event ${JSON.stringify(`/${[...item.targetStatePath, item.targetEventName].join('.')}`)} receives conflicting display names ${JSON.stringify(existingEvent.extraName)} and ${JSON.stringify(item.mappingExtraName)}.`
            );
        }

        if (existingEvent.extraName === undefined && finalExtraName !== undefined) {
            existingEvent.displayName = finalExtraName;
            existingEvent.extraName = finalExtraName;
            existingEvent.extra_name = finalExtraName;
        }
    }
}

function applyImportEventMappings(
    program: FcstmAstDocument,
    hostProgram: FcstmAstDocument,
    importItem: FcstmAstImportStatement,
    ownerStatePath: string[],
    resolvedEventMappings: Map<string, ResolvedImportEventMapping>
): Set<string> {
    const sourceEventNames = new Map<string, string | undefined>();
    const pendingRegistrations: PendingEventRegistration[] = [];
    collectEventExtraNames(program.rootState!, [], sourceEventNames);
    rewriteImportedStateEventPaths(
        program.rootState!,
        [],
        sourceEventNames,
        resolvedEventMappings,
        pendingRegistrations
    );
    pruneMappedSourceEventDefinitions(program.rootState!, [], resolvedEventMappings);
    validatePendingEventRegistrations(pendingRegistrations, importItem, ownerStatePath);
    if (hostProgram.rootState) {
        synthesizeHostEventsForImport(hostProgram.rootState, pendingRegistrations);
    }

    return new Set(
        pendingRegistrations.map(item => pathKey([...item.targetStatePath.slice(1), item.targetEventName]))
    );
}

function rewriteActionRefPath(action: FcstmAstAction, instancePrefix: string[]): void {
    if (action.mode !== 'ref' || !action.refPath || !action.refPath.isAbsolute) {
        return;
    }

    action.refPath.path = [...instancePrefix, ...action.refPath.path];
    action.refPath.segments = [...action.refPath.path];
    action.refPath.text = chainPathText(action.refPath.path, true);
}

function rewriteAbsolutePathsForImportedRoot(
    node: FcstmAstStateDefinition,
    instancePrefix: string[],
    preservedAbsoluteEventPaths: Set<string>
): void {
    for (const transition of node.transitions) {
        if (
            transition.eventId
            && transition.eventId.isAbsolute
            && !preservedAbsoluteEventPaths.has(pathKey(transition.eventId.path))
        ) {
            transition.eventId.path = [...instancePrefix, ...transition.eventId.path];
            transition.eventId.segments = [...transition.eventId.path];
            transition.eventId.text = chainPathText(transition.eventId.path, true);
        }
    }

    for (const transition of node.forceTransitions) {
        if (
            transition.eventId
            && transition.eventId.isAbsolute
            && !preservedAbsoluteEventPaths.has(pathKey(transition.eventId.path))
        ) {
            transition.eventId.path = [...instancePrefix, ...transition.eventId.path];
            transition.eventId.segments = [...transition.eventId.path];
            transition.eventId.text = chainPathText(transition.eventId.path, true);
        }
    }

    for (const action of node.enters) {
        rewriteActionRefPath(action, instancePrefix);
    }
    for (const action of node.durings) {
        rewriteActionRefPath(action, instancePrefix);
    }
    for (const action of node.exits) {
        rewriteActionRefPath(action, instancePrefix);
    }
    for (const action of node.duringAspects) {
        rewriteActionRefPath(action, instancePrefix);
    }

    for (const substate of node.substates) {
        rewriteAbsolutePathsForImportedRoot(
            substate,
            instancePrefix,
            preservedAbsoluteEventPaths
        );
    }
}

function assembleProgramImports(
    program: FcstmAstDocument,
    filePath: string,
    snapshot: WorkspaceAssemblySnapshotLike,
    importLookup: Map<string, FcstmSemanticImport>,
    hostExplicitDefNames: Set<string>,
    assembleNestedProgram: (targetFile: string) => FcstmAstDocument | null
): void {
    if (!program.rootState) {
        throw new Error('State machine document does not contain a root state.');
    }

    const assembleState = (
        node: FcstmAstStateDefinition,
        currentStatePath: string[]
    ): void => {
        const occupiedNames = new Set(node.substates.map(item => item.name));
        const importedSubstates: FcstmAstStateDefinition[] = [];

        for (const importItem of node.imports) {
            if (occupiedNames.has(importItem.alias)) {
                throw new Error(
                    `Import alias conflict in state ${JSON.stringify(currentStatePath.join('.'))}: alias ${JSON.stringify(importItem.alias)} conflicts with an existing child state.`
                );
            }
            occupiedNames.add(importItem.alias);

            const semanticImport = importLookup.get(importLookupKey(currentStatePath, importItem.alias));
            if (!semanticImport?.entryFile) {
                continue;
            }

            const importedProgram = assembleNestedProgram(semanticImport.entryFile);
            if (!importedProgram?.rootState) {
                continue;
            }

            applyImportDefMappings(importedProgram, importItem, currentStatePath);
            mergeImportedDefinitions(program, importedProgram, hostExplicitDefNames);

            const importedRoot = importedProgram.rootState;
            const eventMappings = resolveImportEventMappings(importItem, currentStatePath);
            importedRoot.name = importItem.alias;
            importedRoot.displayName = importItem.extraName || importedRoot.displayName;
            importedRoot.extraName = importItem.extraName || importedRoot.extraName;
            importedRoot.extra_name = importItem.extraName || importedRoot.extra_name;
            const preservedAbsoluteEventPaths = applyImportEventMappings(
                importedProgram,
                program,
                importItem,
                currentStatePath,
                eventMappings
            );
            rewriteAbsolutePathsForImportedRoot(
                importedRoot,
                [...currentStatePath.slice(1), importItem.alias],
                preservedAbsoluteEventPaths
            );
            importedSubstates.push(importedRoot);
        }

        node.imports = [];

        for (const substate of node.substates) {
            assembleState(substate, [...currentStatePath, substate.name]);
        }

        node.substates = [...importedSubstates, ...node.substates];
        node.composite = node.substates.length > 0;
    };

    assembleState(program.rootState, [program.rootState.name]);
}

function assembleAstDocumentImports(
    rootFile: string,
    snapshot: WorkspaceAssemblySnapshotLike
): FcstmAstDocument | null {
    const cache = new Map<string, FcstmAstDocument | null>();
    const visiting = new Set<string>();

    const assembleProgramForFile = (filePath: string): FcstmAstDocument | null => {
        if (cache.has(filePath)) {
            return cloneAstValue(cache.get(filePath) ?? null);
        }
        if (visiting.has(filePath)) {
            return null;
        }

        const node = snapshot.nodes[filePath];
        if (!node?.ast || !node.semantic) {
            cache.set(filePath, node?.ast || null);
            return cloneAstValue(node?.ast || null);
        }

        visiting.add(filePath);
        try {
            const program = cloneAstValue(node.ast);
            const hostExplicitDefNames = new Set(program.definitions.map(item => item.name));
            const importLookup = buildImportLookup(node.semantic.imports);
            assembleProgramImports(
                program,
                filePath,
                snapshot,
                importLookup,
                hostExplicitDefNames,
                assembleProgramForFile
            );
            cache.set(filePath, program);
            return cloneAstValue(program);
        } finally {
            visiting.delete(filePath);
        }
    };

    return assembleProgramForFile(rootFile);
}

export function buildStateMachineModelFromWorkspaceSnapshot(
    snapshot: WorkspaceAssemblySnapshotLike,
    rootFile: string
): FcstmStateMachineModel | null {
    const assembledAst = assembleAstDocumentImports(rootFile, snapshot);
    return buildStateMachineModelFromAst(assembledAst);
}
