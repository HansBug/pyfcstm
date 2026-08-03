import type {
    FcstmDiagramDetailLevel,
    FcstmDiagramPreviewOptions,
    FcstmDiagramPreviewOptionsInput,
    ResolvedFcstmDiagramPreviewOptions,
} from './model';

const DEFAULT_EVENT_NAME_FORMAT = ['extra_name', 'relpath'] as const;

const DETAIL_LEVEL_DEFAULTS: Record<FcstmDiagramDetailLevel, Omit<
    ResolvedFcstmDiagramPreviewOptions,
    'detailLevel' | 'direction' | 'eventNameFormat' | 'maxStateEvents' | 'maxStateActions' | 'maxTransitionEffectLines' | 'maxLabelLength'
>> = {
    minimal: {
        showVariableDefinitions: true,
        showEvents: true,
        showTransitionGuards: true,
        showTransitionEffects: true,
        transitionEffectMode: 'inline',
        eventVisualizationMode: 'legend',
        showStateEvents: false,
        showStateActions: false,
    },
    // `normal` is the default, and a state's own events stay out of its body
    // here so that turning the presets on did not silently redraw every diagram
    // anyone had already made. The level still differs from `minimal` -- it puts
    // transition effects in a note and tints edges by event -- and `full` is
    // where a state's events and actions appear.
    normal: {
        showVariableDefinitions: true,
        showEvents: true,
        showTransitionGuards: true,
        showTransitionEffects: true,
        transitionEffectMode: 'note',
        eventVisualizationMode: 'both',
        showStateEvents: false,
        showStateActions: false,
    },
    full: {
        showVariableDefinitions: true,
        showEvents: true,
        showTransitionGuards: true,
        showTransitionEffects: true,
        transitionEffectMode: 'note',
        eventVisualizationMode: 'both',
        showStateEvents: true,
        showStateActions: true,
    },
};

/**
 * Resolve preview options into a renderer-ready config.
 */
export function resolveFcstmDiagramPreviewOptions(
    input: FcstmDiagramPreviewOptionsInput = undefined
): ResolvedFcstmDiagramPreviewOptions {
    const raw: Partial<FcstmDiagramPreviewOptions> = typeof input === 'string'
        ? {detailLevel: input}
        : (input || {});
    const detailLevel = raw.detailLevel || 'normal';
    const detailDefaults = DETAIL_LEVEL_DEFAULTS[detailLevel];

    let transitionEffectMode = raw.transitionEffectMode || detailDefaults.transitionEffectMode;
    let showTransitionEffects = raw.showTransitionEffects ?? detailDefaults.showTransitionEffects;
    // `transitionEffectMode` and `showTransitionEffects` say overlapping things,
    // so one has to give way when they disagree. A mode the caller named wins:
    // it is the more specific statement, and the flag beside it may only be
    // there because a previous resolve filled it in.
    //
    // The other order made `hide` a state nothing could leave. Choosing it sets
    // the flag false; hand that back and the flag is no longer a default but a
    // choice, so naming `note` afterwards was overruled and the mode snapped
    // back to `hide` -- for good, since no control writes the flag directly.
    // The standalone viewer does hand it back, from two places, and its effect
    // control died after one use. See
    // [issue #421](https://github.com/HansBug/pyfcstm/issues/421).
    //
    // Feeding a resolved set back in is still the wrong shape and still costs
    // the preset its say over anything already decided; this only means it can
    // no longer trap the effect mode.
    if (transitionEffectMode === 'hide') {
        showTransitionEffects = false;
    } else if (raw.transitionEffectMode !== undefined) {
        // Named a mode, so effects are wanted: the three downstream readers all
        // gate on the flag, and leaving it false would show `note` in the
        // control while drawing no notes at all.
        showTransitionEffects = true;
    } else if (!showTransitionEffects) {
        transitionEffectMode = 'hide';
    }

    return {
        detailLevel,
        direction: raw.direction || 'TB',
        showVariableDefinitions: raw.showVariableDefinitions ?? detailDefaults.showVariableDefinitions,
        showEvents: raw.showEvents ?? detailDefaults.showEvents,
        eventNameFormat: raw.eventNameFormat && raw.eventNameFormat.length > 0
            ? [...raw.eventNameFormat]
            : [...DEFAULT_EVENT_NAME_FORMAT],
        showTransitionGuards: raw.showTransitionGuards ?? detailDefaults.showTransitionGuards,
        showTransitionEffects,
        transitionEffectMode,
        eventVisualizationMode: raw.eventVisualizationMode || detailDefaults.eventVisualizationMode,
        showStateEvents: raw.showStateEvents ?? detailDefaults.showStateEvents,
        showStateActions: raw.showStateActions ?? detailDefaults.showStateActions,
        maxStateEvents: raw.maxStateEvents ?? 4,
        maxStateActions: raw.maxStateActions ?? 4,
        maxTransitionEffectLines: raw.maxTransitionEffectLines ?? 8,
        maxLabelLength: raw.maxLabelLength ?? 160,
    };
}
