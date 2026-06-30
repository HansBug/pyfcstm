import {StateMachine, Transition} from '../../model/runtime';
import type {ModelDiagnosticJson, ModelSpanJson} from '../inspect';

interface ComboOriginRefLike {
    origin_id: string;
    term_index: number;
    role: string;
    consumes_term: boolean;
    term_text: string;
    transition_span?: ModelSpanJson | null;
    trigger_span?: ModelSpanJson | null;
    term_span?: ModelSpanJson | null;
    value_span?: ModelSpanJson | null;
    removal_span?: ModelSpanJson | null;
}

interface ComboTerm {
    ref: ComboOriginRefLike;
    transition: Transition;
}

// Solver-backed combo guard warnings are Python-only and consumed through
// inspect JSON. Keep jsfcstm local analysis limited to structural combo
// warnings that do not require Z3 or an approximate mini solver.
export function collectComboWarnings(machine: StateMachine | null | undefined): ModelDiagnosticJson[] {
    if (!machine) return [];
    const termsByOrigin = comboTermsByOrigin(machine);
    const diagnostics: ModelDiagnosticJson[] = [];
    for (const terms of termsByOrigin.values()) {
        diagnostics.push(...duplicateEventWarnings(terms));
    }
    return diagnostics;
}

function comboTermsByOrigin(machine: StateMachine): Map<string, ComboTerm[]> {
    const grouped = new Map<string, Map<number, ComboTerm>>();
    for (const transition of machine.allTransitions) {
        for (const rawRef of transition.combo_origin_refs ?? []) {
            const ref = comboOriginRef(rawRef);
            if (!ref || !ref.consumes_term) continue;
            let byIndex = grouped.get(ref.origin_id);
            if (!byIndex) {
                byIndex = new Map<number, ComboTerm>();
                grouped.set(ref.origin_id, byIndex);
            }
            if (!byIndex.has(ref.term_index)) {
                byIndex.set(ref.term_index, {ref, transition});
            }
        }
    }
    const out = new Map<string, ComboTerm[]>();
    for (const [originId, byIndex] of grouped.entries()) {
        out.set(originId, Array.from(byIndex.values()).sort((a, b) => a.ref.term_index - b.ref.term_index));
    }
    return out;
}

function comboOriginRef(value: unknown): ComboOriginRefLike | null {
    if (typeof value !== 'object' || value === null) return null;
    const item = value as Record<string, unknown>;
    if (
        typeof item.origin_id !== 'string' ||
        typeof item.term_index !== 'number' ||
        typeof item.role !== 'string' ||
        typeof item.consumes_term !== 'boolean' ||
        typeof item.term_text !== 'string'
    ) {
        return null;
    }
    return {
        origin_id: item.origin_id,
        term_index: item.term_index,
        role: item.role,
        consumes_term: item.consumes_term,
        term_text: item.term_text,
        transition_span: item.transition_span as ModelSpanJson | null | undefined,
        trigger_span: item.trigger_span as ModelSpanJson | null | undefined,
        term_span: item.term_span as ModelSpanJson | null | undefined,
        value_span: item.value_span as ModelSpanJson | null | undefined,
        removal_span: item.removal_span as ModelSpanJson | null | undefined,
    };
}

function duplicateEventWarnings(terms: ComboTerm[]): ModelDiagnosticJson[] {
    const diagnostics: ModelDiagnosticJson[] = [];
    const firstByEvent = new Map<string, ComboTerm>();
    for (const term of terms) {
        if (!term.transition.event) continue;
        const eventName = term.transition.event.pathName;
        const first = firstByEvent.get(eventName);
        if (!first) {
            firstByEvent.set(eventName, term);
            continue;
        }
        diagnostics.push({
            code: 'W_COMBO_DUPLICATE_EVENT',
            severity: 'warning',
            message: `Combo trigger repeats event ${JSON.stringify(eventName)}; this is legal but usually redundant.`,
            span: term.ref.term_span ?? null,
            refs: {
                origin_id: term.ref.origin_id,
                event_name: eventName,
                term_index: term.ref.term_index,
                first_term_index: first.ref.term_index,
                term_text: term.ref.term_text,
                first_term_text: first.ref.term_text,
                transition_span: term.ref.transition_span ?? null,
                trigger_span: term.ref.trigger_span ?? null,
                term_span: term.ref.term_span ?? null,
                first_term_span: first.ref.term_span ?? null,
            },
        });
    }
    return diagnostics;
}
