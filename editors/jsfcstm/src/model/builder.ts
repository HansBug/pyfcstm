import type {
    FcstmAstAction,
    FcstmAstChainPath,
    FcstmAstDocument,
    FcstmAstExpression,
    FcstmAstForcedTransition,
    FcstmAstIfBranch,
    FcstmAstIfStatement,
    FcstmAstOperationStatement,
    FcstmAstStateDefinition,
    FcstmAstTransition,
    FcstmAstVariableDefinition,
} from '../ast';
import type {FcstmSemanticDocument} from '../semantics';
import type {
    FcstmModelActionPath,
    RawFcstmModelBinaryOp as FcstmModelBinaryOp,
    RawFcstmModelBoolean as FcstmModelBoolean,
    RawFcstmModelConditionalOp as FcstmModelConditionalOp,
    RawFcstmModelEvent as FcstmModelEvent,
    RawFcstmModelExpression as FcstmModelExpression,
    RawFcstmModelFloat as FcstmModelFloat,
    RawFcstmModelIfBlock as FcstmModelIfBlock,
    RawFcstmModelIfBlockBranch as FcstmModelIfBlockBranch,
    RawFcstmModelInteger as FcstmModelInteger,
    RawFcstmModelNamedFunction as FcstmModelNamedFunction,
    RawFcstmModelOnAspect as FcstmModelOnAspect,
    RawFcstmModelOnStage as FcstmModelOnStage,
    RawFcstmModelOperation as FcstmModelOperation,
    RawFcstmModelOperationStatement as FcstmModelOperationStatement,
    RawFcstmModelState as FcstmModelState,
    RawFcstmModelStateMachine as FcstmRawStateMachine,
    RawFcstmModelTransition as FcstmModelTransition,
    RawFcstmModelUFunc as FcstmModelUFunc,
    RawFcstmModelUnaryOp as FcstmModelUnaryOp,
    RawFcstmModelVarDefine as FcstmModelVarDefine,
    RawFcstmModelVariable as FcstmModelVariable,
} from './raw';
import {hydrateStateMachine, type FcstmModelStateMachine as FcstmRuntimeStateMachine} from './runtime';

const MATH_CONSTANTS: Record<string, number> = {
    E: Math.E,
    pi: Math.PI,
    tau: Math.PI * 2,
};

interface InheritedForceTransition {
    fromStateName: 'ALL' | string;
    toState: 'EXIT_STATE' | string;
    event?: FcstmModelEvent;
    guard?: FcstmModelExpression;
    range: FcstmModelTransition['range'];
    text: string;
    declaredInStatePath: string[];
    triggerScope?: 'local' | 'chain' | 'absolute';
    transitionKind: FcstmModelTransition['transitionKind'];
}

function pathKey(path: Array<string | null>): string {
    return path.map(segment => segment === null ? '<unnamed>' : segment).join('.');
}

function statePathName(path: string[]): string {
    return path.join('.');
}

function actionPathName(path: FcstmModelActionPath): string {
    return path.map(segment => segment === null ? '<unnamed>' : segment).join('.');
}

function parseNumberLiteral(raw: string): number {
    if (/^0x/i.test(raw)) {
        return parseInt(raw, 16);
    }
    if (/^0b/i.test(raw)) {
        return parseInt(raw.slice(2), 2);
    }
    return Number(raw);
}

function isSemanticDocument(
    source: FcstmAstDocument | FcstmSemanticDocument | null
): source is FcstmSemanticDocument {
    return Boolean(source && source.kind === 'semanticDocument');
}

class StateMachineModelBuilder {
    private readonly filePath: string;
    private readonly rootStateName: string;
    private readonly defines: Record<string, FcstmModelVarDefine> = {};
    private readonly allStates: FcstmModelState[] = [];
    private readonly allEvents: FcstmModelEvent[] = [];
    private readonly allTransitions: FcstmModelTransition[] = [];
    private readonly allActions: FcstmModelNamedFunction[] = [];
    private readonly statesByPath = new Map<string, FcstmModelState>();
    private readonly stateAstByPath = new Map<string, FcstmAstStateDefinition>();
    private readonly eventsByPath = new Map<string, FcstmModelEvent>();
    private readonly namedFunctionsByPath = new Map<string, FcstmModelNamedFunction>();

    constructor(private readonly ast: FcstmAstDocument) {
        this.filePath = ast.filePath;
        this.rootStateName = ast.rootState?.name || '';
    }

    build(): FcstmRuntimeStateMachine | null {
        if (!this.ast.rootState) {
            return null;
        }

        for (const definition of this.ast.variables) {
            this.defines[definition.name] = this.buildVarDefine(definition);
        }

        const rootState = this.buildState(this.ast.rootState, undefined);
        this.finalizeActionReferences();
        this.finalizeTransitions(this.ast.rootState, rootState, []);

        const transitionsByParentPath: Record<string, FcstmModelTransition[]> = {};
        for (const transition of this.allTransitions) {
            const key = statePathName(transition.parentPath);
            if (!transitionsByParentPath[key]) {
                transitionsByParentPath[key] = [];
            }
            transitionsByParentPath[key].push(transition);
        }

        const lookups = {
            definesByName: this.defines,
            statesByPath: Object.fromEntries(this.statesByPath.entries()),
            eventsByPathName: Object.fromEntries(this.eventsByPath.entries()),
            namedFunctionsByPath: Object.fromEntries(this.namedFunctionsByPath.entries()),
            transitionsByParentPath,
        };

        const rawStateMachine: FcstmRawStateMachine = {
            kind: 'stateMachine',
            pyModelType: 'StateMachine',
            range: this.ast.range,
            text: this.ast.text,
            filePath: this.filePath,
            defines: this.defines,
            rootState,
            root_state: rootState,
            allStates: this.allStates,
            all_states: this.allStates,
            allEvents: this.allEvents,
            all_events: this.allEvents,
            allTransitions: this.allTransitions,
            all_transitions: this.allTransitions,
            allActions: this.allActions,
            all_actions: this.allActions,
            lookups,
        };
        return hydrateStateMachine(rawStateMachine);
    }

    private buildVarDefine(definition: FcstmAstVariableDefinition): FcstmModelVarDefine {
        return {
            kind: 'varDefine',
            pyModelType: 'VarDefine',
            range: definition.range,
            text: definition.text,
            name: definition.name,
            type: definition.valueType,
            init: this.buildExpression(definition.initializer),
        };
    }

    private buildState(
        definition: FcstmAstStateDefinition,
        parent: FcstmModelState | undefined
    ): FcstmModelState {
        const path = parent ? [...parent.path, definition.name] : [definition.name];
        const substates: Record<string, FcstmModelState> = {};
        const events: Record<string, FcstmModelEvent> = {};
        const transitions: FcstmModelTransition[] = [];
        const namedFunctions: Record<string, FcstmModelNamedFunction> = {};
        const onEnters: FcstmModelOnStage[] = [];
        const onDurings: FcstmModelOnStage[] = [];
        const onExits: FcstmModelOnStage[] = [];
        const onDuringAspects: FcstmModelOnAspect[] = [];

        const state: FcstmModelState = {
            kind: 'state',
            pyModelType: 'State',
            range: definition.range,
            text: definition.text,
            name: definition.name,
            path,
            pathName: statePathName(path),
            path_name: statePathName(path),
            substates,
            events,
            transitions,
            namedFunctions,
            named_functions: namedFunctions,
            onEnters,
            on_enters: onEnters,
            onDurings,
            on_durings: onDurings,
            onExits,
            on_exits: onExits,
            onDuringAspects,
            on_during_aspects: onDuringAspects,
            parentPath: parent?.path,
            parent_path: parent?.path,
            substateNameToId: {},
            substate_name_to_id: {},
            extraName: definition.displayName,
            extra_name: definition.displayName,
            isPseudo: definition.pseudo,
            is_pseudo: definition.pseudo,
            isLeafState: definition.substates.length === 0,
            is_leaf_state: definition.substates.length === 0,
            isRootState: !parent,
            is_root_state: !parent,
            isStoppable: definition.substates.length === 0 && !definition.pseudo,
            is_stoppable: definition.substates.length === 0 && !definition.pseudo,
        };

        this.allStates.push(state);
        this.statesByPath.set(state.pathName, state);
        this.stateAstByPath.set(state.pathName, definition);

        for (const substate of definition.substates) {
            if (!substates[substate.name]) {
                substates[substate.name] = this.buildState(substate, state);
            }
        }

        const substateNameToId = Object.fromEntries(Object.keys(substates).map((name, index) => [name, index]));
        state.substateNameToId = substateNameToId;
        state.substate_name_to_id = substateNameToId;

        for (const action of definition.enters) {
            onEnters.push(this.buildOnStage(action, state));
        }
        for (const action of definition.durings) {
            onDurings.push(this.buildOnStage(action, state));
        }
        for (const action of definition.exits) {
            onExits.push(this.buildOnStage(action, state));
        }
        for (const action of definition.duringAspects) {
            onDuringAspects.push(this.buildOnAspect(action, state));
        }

        for (const event of definition.events) {
            this.ensureEvent(state.path, event.name, event.range, event.text, {
                declared: true,
                origin: 'declared',
                extraName: event.displayName,
            });
        }

        return state;
    }

    private buildOnStage(action: FcstmAstAction, ownerState: FcstmModelState): FcstmModelOnStage {
        const built = this.buildActionBase(action, ownerState, false) as FcstmModelOnStage;
        built.kind = 'onStage';
        built.pyModelType = 'OnStage';
        this.registerNamedFunction(built);
        return built;
    }

    private buildOnAspect(action: FcstmAstAction, ownerState: FcstmModelState): FcstmModelOnAspect {
        const built = this.buildActionBase(action, ownerState, true) as FcstmModelOnAspect;
        built.kind = 'onAspect';
        built.pyModelType = 'OnAspect';
        built.stage = 'during';
        built.isAspect = true;
        built.is_aspect = true;
        this.registerNamedFunction(built);
        return built;
    }

    private buildActionBase(
        action: FcstmAstAction,
        ownerState: FcstmModelState,
        isAspect: boolean
    ): FcstmModelOnStage | FcstmModelOnAspect {
        const statePath: FcstmModelActionPath = [...ownerState.path, action.name ?? null];
        const refStatePath = action.refPath
            ? action.refPath.isAbsolute
                ? [this.rootStateName, ...action.refPath.segments]
                : [...ownerState.path, ...action.refPath.segments]
            : undefined;
        const built: FcstmModelOnStage | FcstmModelOnAspect = {
            kind: 'onStage',
            pyModelType: 'OnStage',
            range: action.range,
            text: action.text,
            stage: action.stage,
            aspect: action.aspect,
            name: action.name,
            doc: action.doc,
            operations: this.buildOperationStatements(action.operationsList),
            isAbstract: action.mode === 'abstract',
            is_abstract: action.mode === 'abstract',
            isRef: action.mode === 'ref',
            is_ref: action.mode === 'ref',
            isAspect: isAspect,
            is_aspect: isAspect,
            mode: action.mode,
            statePath,
            state_path: statePath,
            funcName: actionPathName(statePath),
            func_name: actionPathName(statePath),
            parentPath: ownerState.path,
            parent_path: ownerState.path,
            refStatePath,
            ref_state_path: refStatePath,
            refResolved: false,
            ref_resolved: false,
        };

        this.allActions.push(built);
        return built;
    }

    private registerNamedFunction(action: FcstmModelNamedFunction): void {
        if (!action.name) {
            return;
        }

        const ownerState = this.statesByPath.get(statePathName(action.parentPath));
        if (ownerState && !ownerState.namedFunctions[action.name]) {
            ownerState.namedFunctions[action.name] = action;
        }

        const lookupKey = actionPathName(action.statePath);
        if (!this.namedFunctionsByPath.has(lookupKey)) {
            this.namedFunctionsByPath.set(lookupKey, action);
        }
    }

    private finalizeActionReferences(): void {
        for (const action of this.allActions) {
            if (!action.refStatePath) {
                continue;
            }

            const target = this.namedFunctionsByPath.get(statePathName(action.refStatePath));
            if (!target) {
                continue;
            }

            action.refResolved = true;
            action.ref_resolved = true;
            action.refTargetQualifiedName = target.funcName;
            action.ref_target_qualified_name = target.funcName;
        }
    }

    private finalizeTransitions(
        definition: FcstmAstStateDefinition,
        currentState: FcstmModelState,
        inheritedForceTransitions: InheritedForceTransition[]
    ): void {
        const effectiveForceTransitions = [
            ...inheritedForceTransitions,
            ...definition.forceTransitions.map(force => this.buildForceTransition(force, currentState)),
        ];

        for (const substateDefinition of definition.substates) {
            const nextState = currentState.substates[substateDefinition.name];
            const childInheritedTransitions: InheritedForceTransition[] = [];

            for (const force of effectiveForceTransitions) {
                if (force.fromStateName !== 'ALL' && force.fromStateName !== substateDefinition.name) {
                    continue;
                }

                this.pushTransition({
                    range: force.range,
                    text: force.text,
                    fromState: substateDefinition.name,
                    toState: force.toState,
                    event: force.event,
                    guard: force.guard,
                    effects: [],
                    parentState: currentState,
                    sourceKind: 'state',
                    targetKind: force.toState === 'EXIT_STATE' ? 'exit' : 'state',
                    transitionKind: force.transitionKind,
                    forced: true,
                    declaredInStatePath: force.declaredInStatePath,
                    triggerScope: force.triggerScope,
                });

                childInheritedTransitions.push({
                    fromStateName: 'ALL',
                    toState: 'EXIT_STATE',
                    event: force.event,
                    guard: force.guard,
                    range: force.range,
                    text: force.text,
                    declaredInStatePath: force.declaredInStatePath,
                    triggerScope: force.triggerScope,
                    transitionKind: 'exitAll',
                });
            }

            this.finalizeTransitions(substateDefinition, nextState, childInheritedTransitions);
        }

        for (const transition of definition.transitions) {
            const triggerScope = this.getTriggerScope(transition);
            const event = transition.eventId
                ? this.resolveEventReference(currentState, transition.eventId, transition.trigger?.range || transition.range, triggerScope)
                : undefined;
            const targetKind = transition.targetKind === 'exit' ? 'exit' : 'state';
            this.pushTransition({
                range: transition.range,
                text: transition.text,
                fromState: transition.sourceKind === 'init' ? 'INIT_STATE' : (transition.sourceStateName || 'INIT_STATE'),
                toState: targetKind === 'exit' ? 'EXIT_STATE' : (transition.targetStateName || 'EXIT_STATE'),
                event,
                guard: transition.guard ? this.buildExpression(transition.guard) : undefined,
                effects: this.buildOperationStatements(transition.postOperations),
                parentState: currentState,
                sourceKind: transition.sourceKind === 'init' ? 'init' : 'state',
                targetKind,
                transitionKind: transition.transitionKind,
                forced: false,
                declaredInStatePath: currentState.path,
                triggerScope,
            });
        }
    }

    private buildForceTransition(
        transition: FcstmAstForcedTransition,
        currentState: FcstmModelState
    ): InheritedForceTransition {
        const triggerScope = this.getTriggerScope(transition);
        const event = transition.eventId
            ? this.resolveEventReference(currentState, transition.eventId, transition.trigger?.range || transition.range, triggerScope)
            : undefined;
        return {
            fromStateName: transition.sourceKind === 'all'
                ? 'ALL'
                : (transition.sourceStateName || 'ALL'),
            toState: transition.targetKind === 'exit'
                ? 'EXIT_STATE'
                : (transition.targetStateName || 'EXIT_STATE'),
            event,
            guard: transition.guard ? this.buildExpression(transition.guard) : undefined,
            range: transition.range,
            text: transition.text,
            declaredInStatePath: currentState.path,
            triggerScope,
            transitionKind: transition.transitionKind,
        };
    }

    private getTriggerScope(
        transition: FcstmAstTransition | FcstmAstForcedTransition
    ): 'local' | 'chain' | 'absolute' | undefined {
        if (!transition.trigger) {
            return undefined;
        }
        if (transition.trigger.kind === 'localTrigger') {
            return 'local';
        }
        return transition.trigger.eventPath.isAbsolute ? 'absolute' : 'chain';
    }

    private resolveEventReference(
        currentState: FcstmModelState,
        eventPath: FcstmAstChainPath,
        range: FcstmModelEvent['range'],
        origin: 'local' | 'chain' | 'absolute' | undefined
    ): FcstmModelEvent | undefined {
        if (eventPath.segments.length === 0) {
            return undefined;
        }

        let ownerState = eventPath.isAbsolute
            ? this.statesByPath.get(this.rootStateName)
            : currentState;
        if (!ownerState) {
            return undefined;
        }

        for (const segment of eventPath.segments.slice(0, -1)) {
            ownerState = ownerState.substates[segment] || this.resolveStateReference(ownerState.path, segment);
            if (!ownerState) {
                return undefined;
            }
        }

        return this.ensureEvent(ownerState.path, eventPath.segments[eventPath.segments.length - 1], range, eventPath.text, {
            declared: false,
            origin: origin || (eventPath.isAbsolute ? 'absolute' : 'chain'),
        });
    }

    private ensureEvent(
        statePath: string[],
        eventName: string,
        range: FcstmModelEvent['range'],
        text: string,
        options: {
            declared: boolean;
            origin: 'declared' | 'local' | 'chain' | 'absolute';
            extraName?: string;
        }
    ): FcstmModelEvent | undefined {
        const ownerState = this.statesByPath.get(statePathName(statePath));
        if (!ownerState) {
            return undefined;
        }

        const eventPath = [...statePath, eventName];
        const eventPathName = statePathName(eventPath);
        let event = this.eventsByPath.get(eventPathName);

        if (!event) {
            event = {
                kind: 'event',
                pyModelType: 'Event',
                range,
                text,
                name: eventName,
                statePath,
                state_path: statePath,
                path: eventPath,
                pathName: eventPathName,
                path_name: eventPathName,
                extraName: options.extraName,
                extra_name: options.extraName,
                declared: options.declared,
                origins: [options.origin],
            };
            this.eventsByPath.set(eventPathName, event);
            this.allEvents.push(event);
        } else {
            event.declared = event.declared || options.declared;
            event.extraName = event.extraName || options.extraName;
            event.extra_name = event.extra_name || options.extraName;
            if (!event.origins.includes(options.origin)) {
                event.origins.push(options.origin);
            }
        }

        ownerState.events[eventName] = event;
        return event;
    }

    private pushTransition(params: {
        range: FcstmModelTransition['range'];
        text: string;
        fromState: FcstmModelTransition['fromState'];
        toState: FcstmModelTransition['toState'];
        event?: FcstmModelEvent;
        guard?: FcstmModelExpression;
        effects: FcstmModelOperationStatement[];
        parentState: FcstmModelState;
        sourceKind: FcstmModelTransition['sourceKind'];
        targetKind: FcstmModelTransition['targetKind'];
        transitionKind: FcstmModelTransition['transitionKind'];
        forced: boolean;
        declaredInStatePath: string[];
        triggerScope?: FcstmModelTransition['triggerScope'];
    }): void {
        const transition: FcstmModelTransition = {
            kind: 'transition',
            pyModelType: 'Transition',
            range: params.range,
            text: params.text,
            fromState: params.fromState,
            from_state: params.fromState,
            toState: params.toState,
            to_state: params.toState,
            event: params.event,
            guard: params.guard,
            effects: params.effects,
            parentPath: params.parentState.path,
            parent_path: params.parentState.path,
            sourceStatePath: params.fromState === 'INIT_STATE'
                ? undefined
                : this.resolveStateReference(params.parentState.path, params.fromState)?.path,
            source_state_path: params.fromState === 'INIT_STATE'
                ? undefined
                : this.resolveStateReference(params.parentState.path, params.fromState)?.path,
            targetStatePath: params.toState === 'EXIT_STATE'
                ? undefined
                : this.resolveStateReference(params.parentState.path, params.toState)?.path,
            target_state_path: params.toState === 'EXIT_STATE'
                ? undefined
                : this.resolveStateReference(params.parentState.path, params.toState)?.path,
            sourceKind: params.sourceKind,
            targetKind: params.targetKind,
            transitionKind: params.transitionKind,
            forced: params.forced,
            declaredInStatePath: params.declaredInStatePath,
            declared_in_state_path: params.declaredInStatePath,
            triggerScope: params.triggerScope,
            trigger_scope: params.triggerScope,
        };

        params.parentState.transitions.push(transition);
        this.allTransitions.push(transition);
    }

    private resolveStateReference(
        ownerStatePath: string[],
        stateName: string
    ): FcstmModelState | undefined {
        if (this.rootStateName && stateName === this.rootStateName) {
            return this.statesByPath.get(this.rootStateName);
        }

        for (let length = ownerStatePath.length; length >= 1; length -= 1) {
            const candidatePath = [...ownerStatePath.slice(0, length), stateName];
            const candidate = this.statesByPath.get(statePathName(candidatePath));
            if (candidate) {
                return candidate;
            }
        }

        const globalMatches = this.allStates.filter(state => state.name === stateName);
        return globalMatches.length === 1 ? globalMatches[0] : undefined;
    }

    private buildOperationStatements(
        statements: FcstmAstOperationStatement[]
    ): FcstmModelOperationStatement[] {
        const built: FcstmModelOperationStatement[] = [];
        for (const statement of statements) {
            const item = this.buildOperationStatement(statement);
            if (item) {
                built.push(item);
            }
        }
        return built;
    }

    private buildOperationStatement(
        statement: FcstmAstOperationStatement
    ): FcstmModelOperationStatement | null {
        if (statement.kind === 'emptyStatement') {
            return null;
        }

        if (statement.kind === 'assignmentStatement') {
            const operation: FcstmModelOperation = {
                kind: 'operation',
                pyModelType: 'Operation',
                range: statement.range,
                text: statement.text,
                varName: statement.targetName,
                var_name: statement.targetName,
                expr: this.buildExpression(statement.expression),
            };
            return operation;
        }

        if (statement.kind === 'ifStatement') {
            return this.buildIfBlock(statement);
        }

        return null;
    }

    private buildIfBlock(statement: FcstmAstIfStatement): FcstmModelIfBlock {
        return {
            kind: 'ifBlock',
            pyModelType: 'IfBlock',
            range: statement.range,
            text: statement.text,
            branches: statement.branches.map(branch => this.buildIfBlockBranch(branch)),
        };
    }

    private buildIfBlockBranch(branch: FcstmAstIfBranch): FcstmModelIfBlockBranch {
        return {
            kind: 'ifBlockBranch',
            pyModelType: 'IfBlockBranch',
            range: branch.range,
            text: branch.text,
            condition: branch.condition ? this.buildExpression(branch.condition) : null,
            statements: this.buildOperationStatements(branch.statements),
        };
    }

    private buildExpression(expression: FcstmAstExpression): FcstmModelExpression {
        const originalExpression = expression;
        switch (expression.expressionKind) {
            case 'literal':
                if (expression.pyNodeType === 'Boolean') {
                    const booleanExpr: FcstmModelBoolean = {
                        kind: 'boolean',
                        pyModelType: 'Boolean',
                        range: expression.range,
                        text: expression.text,
                        value: expression.valueText === 'true',
                    };
                    return booleanExpr;
                }
                if (expression.pyNodeType === 'Float') {
                    const floatExpr: FcstmModelFloat = {
                        kind: 'float',
                        pyModelType: 'Float',
                        range: expression.range,
                        text: expression.text,
                        value: Number(expression.valueText),
                    };
                    return floatExpr;
                }
                const integerExpr: FcstmModelInteger = {
                    kind: 'integer',
                    pyModelType: 'Integer',
                    range: expression.range,
                    text: expression.text,
                    value: parseNumberLiteral(expression.valueText),
                };
                return integerExpr;
            case 'identifier': {
                const variableExpr: FcstmModelVariable = {
                    kind: 'variable',
                    pyModelType: 'Variable',
                    range: expression.range,
                    text: expression.text,
                    name: expression.name,
                };
                return variableExpr;
            }
            case 'mathConst': {
                const floatExpr: FcstmModelFloat = {
                    kind: 'float',
                    pyModelType: 'Float',
                    range: expression.range,
                    text: expression.text,
                    value: MATH_CONSTANTS[expression.name],
                };
                return floatExpr;
            }
            case 'unary': {
                const unaryExpr: FcstmModelUnaryOp = {
                    kind: 'unaryOp',
                    pyModelType: 'UnaryOp',
                    range: expression.range,
                    text: expression.text,
                    op: expression.op,
                    x: this.buildExpression(expression.operand),
                };
                return unaryExpr;
            }
            case 'binary': {
                const binaryExpr: FcstmModelBinaryOp = {
                    kind: 'binaryOp',
                    pyModelType: 'BinaryOp',
                    range: expression.range,
                    text: expression.text,
                    x: this.buildExpression(expression.left),
                    op: expression.op,
                    y: this.buildExpression(expression.right),
                };
                return binaryExpr;
            }
            case 'conditional': {
                const ifTrue = this.buildExpression(expression.whenTrue);
                const ifFalse = this.buildExpression(expression.whenFalse);
                const conditionalExpr: FcstmModelConditionalOp = {
                    kind: 'conditionalOp',
                    pyModelType: 'ConditionalOp',
                    range: expression.range,
                    text: expression.text,
                    cond: this.buildExpression(expression.condition),
                    ifTrue,
                    if_true: ifTrue,
                    ifFalse,
                    if_false: ifFalse,
                };
                return conditionalExpr;
            }
            case 'function': {
                const funcExpr: FcstmModelUFunc = {
                    kind: 'ufunc',
                    pyModelType: 'UFunc',
                    range: expression.range,
                    text: expression.text,
                    func: expression.functionName,
                    x: this.buildExpression(expression.argument),
                };
                return funcExpr;
            }
            case 'parenthesized':
                return this.buildExpression(expression.expression);
        }

        const fallbackExpr: FcstmModelVariable = {
            kind: 'variable',
            pyModelType: 'Variable',
            range: originalExpression.range,
            text: originalExpression.text,
            name: originalExpression.text,
        };
        return fallbackExpr;
    }
}

/**
 * Build a stable model-layer state machine from an AST document.
 */
export function buildStateMachineModelFromAst(
    ast: FcstmAstDocument | null
): FcstmRuntimeStateMachine | null {
    if (!ast) {
        return null;
    }

    return new StateMachineModelBuilder(ast).build();
}

/**
 * Build a stable model-layer state machine from a semantic document.
 */
export function buildStateMachineModelFromSemantic(
    semantic: FcstmSemanticDocument | null
): FcstmRuntimeStateMachine | null {
    if (!semantic?.ast) {
        return null;
    }

    return buildStateMachineModelFromAst(semantic.ast);
}

/**
 * Build a stable state-machine model from either AST or semantic input.
 */
export function buildStateMachineModel(
    source: FcstmAstDocument | FcstmSemanticDocument | null
): FcstmRuntimeStateMachine | null {
    if (!source) {
        return null;
    }

    return isSemanticDocument(source)
        ? buildStateMachineModelFromSemantic(source)
        : buildStateMachineModelFromAst(source);
}
