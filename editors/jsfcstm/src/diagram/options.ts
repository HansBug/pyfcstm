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
    normal: {
        showVariableDefinitions: true,
        showEvents: true,
        showTransitionGuards: true,
        showTransitionEffects: true,
        transitionEffectMode: 'note',
        eventVisualizationMode: 'both',
        showStateEvents: true,
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
    if (transitionEffectMode === 'hide') {
        showTransitionEffects = false;
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
