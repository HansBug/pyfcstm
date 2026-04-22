/**
 * FCSTM preview colour palettes.
 *
 * Each palette ships both a light and a dark variant; the webview
 * chooses the variant based on the ambient VSCode theme
 * (``body.vscode-dark`` / ``body.vscode-high-contrast``) and the user's
 * palette pick, so a single selection flows through both modes.
 *
 * Palettes are modelled on well-known IDE / designer themes so the
 * diagram always looks native rather than home-grown:
 *
 *   - ``default``  : current pyfcstm blue-forward flat look.
 *   - ``nord``     : https://www.nordtheme.com — arctic, cool blues.
 *   - ``solarized``: https://ethanschoonover.com/solarized — sepia +
 *                   6 muted accents, great on beige / dark cyan.
 *   - ``darcula``  : JetBrains Darcula-inspired dark theme, with a
 *                   tidy light counterpart.
 */

export type PaletteMode = 'light' | 'dark';
export type PaletteId = 'default' | 'nord' | 'solarized' | 'darcula';

export interface SvgPalette {
    leafFill: string;
    leafStroke: string;
    leafStrokeWidth: number;
    leafRadius: number;
    leafShadowAlpha: number;
    compositeFill: string;
    compositeTitleFill: string;
    compositeStroke: string;
    compositeStrokeWidth: number;
    compositeRadius: number;
    pseudoStateFill: string;
    pseudoStateStroke: string;
    pseudoStrokeWidth: number;
    pseudoDash: string;
    titleColor: string;
    initFill: string;
    exitOuterStroke: string;
    exitInnerFill: string;
    edgeStroke: string;
    edgeLabelHalo: string;
    edgeLabelGuardColor: string;
    edgeLabelEffectColor: string;
    canvasFill: string;
    noteFill: string;
    noteStroke: string;
    noteFoldFill: string;
    chevronBtnFill: string;
    chevronBtnStroke: string;
}

type PaletteVariants = {light: SvgPalette; dark: SvgPalette};

/**
 * The ``default`` palette keeps the look shipped in the initial Vue
 * cutover so existing screenshots still match. Dark variant was added
 * alongside the theme system.
 */
const DEFAULT_LIGHT: SvgPalette = {
    leafFill: '#ffffff',
    leafStroke: '#5a92c4',
    leafStrokeWidth: 1.4,
    leafRadius: 10,
    leafShadowAlpha: 0.18,
    compositeFill: '#edf4fb',
    compositeTitleFill: '#dce9f5',
    compositeStroke: '#2d6aa8',
    compositeStrokeWidth: 1.8,
    compositeRadius: 16,
    pseudoStateFill: '#fdf3e1',
    pseudoStateStroke: '#b07a36',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#183b61',
    initFill: '#2d6aa8',
    exitOuterStroke: '#2d6aa8',
    exitInnerFill: '#2d6aa8',
    edgeStroke: '#3470a8',
    edgeLabelHalo: '#ffffff',
    edgeLabelGuardColor: '#9c5d00',
    edgeLabelEffectColor: '#4a6b8c',
    canvasFill: 'transparent',
    noteFill: '#fffaee',
    noteStroke: '#c79a3d',
    noteFoldFill: '#f3e3b5',
    chevronBtnFill: 'rgba(255,255,255,0.5)',
    chevronBtnStroke: 'rgba(45,106,168,0.25)',
};

const DEFAULT_DARK: SvgPalette = {
    leafFill: '#24303f',
    leafStroke: '#6ea5d5',
    leafStrokeWidth: 1.4,
    leafRadius: 10,
    leafShadowAlpha: 0.35,
    compositeFill: '#1a2634',
    compositeTitleFill: '#26364b',
    compositeStroke: '#6ea5d5',
    compositeStrokeWidth: 1.8,
    compositeRadius: 16,
    pseudoStateFill: '#352e20',
    pseudoStateStroke: '#d4a65e',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#dbe4f0',
    initFill: '#6ea5d5',
    exitOuterStroke: '#6ea5d5',
    exitInnerFill: '#6ea5d5',
    edgeStroke: '#8fb6d9',
    edgeLabelHalo: '#0f1520',
    edgeLabelGuardColor: '#e2b056',
    edgeLabelEffectColor: '#a8bfd8',
    canvasFill: 'transparent',
    noteFill: '#3a3423',
    noteStroke: '#c79a3d',
    noteFoldFill: '#5a4c2b',
    chevronBtnFill: 'rgba(0,0,0,0.35)',
    chevronBtnStroke: 'rgba(142,184,223,0.35)',
};

const NORD_LIGHT: SvgPalette = {
    leafFill: '#eceff4',
    leafStroke: '#5e81ac',
    leafStrokeWidth: 1.4,
    leafRadius: 10,
    leafShadowAlpha: 0.16,
    compositeFill: '#e5e9f0',
    compositeTitleFill: '#d8dee9',
    compositeStroke: '#5e81ac',
    compositeStrokeWidth: 1.8,
    compositeRadius: 16,
    pseudoStateFill: '#ead7b8',
    pseudoStateStroke: '#d08770',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#2e3440',
    initFill: '#5e81ac',
    exitOuterStroke: '#5e81ac',
    exitInnerFill: '#5e81ac',
    edgeStroke: '#81a1c1',
    edgeLabelHalo: '#eceff4',
    edgeLabelGuardColor: '#d08770',
    edgeLabelEffectColor: '#4c566a',
    canvasFill: 'transparent',
    noteFill: '#ebcb8b',
    noteStroke: '#d08770',
    noteFoldFill: '#d8b568',
    chevronBtnFill: 'rgba(255,255,255,0.55)',
    chevronBtnStroke: 'rgba(94,129,172,0.35)',
};

const NORD_DARK: SvgPalette = {
    leafFill: '#3b4252',
    leafStroke: '#88c0d0',
    leafStrokeWidth: 1.4,
    leafRadius: 10,
    leafShadowAlpha: 0.34,
    compositeFill: '#2e3440',
    compositeTitleFill: '#434c5e',
    compositeStroke: '#88c0d0',
    compositeStrokeWidth: 1.8,
    compositeRadius: 16,
    pseudoStateFill: '#4a3f37',
    pseudoStateStroke: '#d08770',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#eceff4',
    initFill: '#88c0d0',
    exitOuterStroke: '#88c0d0',
    exitInnerFill: '#88c0d0',
    edgeStroke: '#81a1c1',
    edgeLabelHalo: '#2e3440',
    edgeLabelGuardColor: '#ebcb8b',
    edgeLabelEffectColor: '#d8dee9',
    canvasFill: 'transparent',
    noteFill: '#4a3f24',
    noteStroke: '#ebcb8b',
    noteFoldFill: '#6b5930',
    chevronBtnFill: 'rgba(0,0,0,0.3)',
    chevronBtnStroke: 'rgba(136,192,208,0.35)',
};

const SOLARIZED_LIGHT: SvgPalette = {
    leafFill: '#fdf6e3',
    leafStroke: '#268bd2',
    leafStrokeWidth: 1.4,
    leafRadius: 10,
    leafShadowAlpha: 0.18,
    compositeFill: '#eee8d5',
    compositeTitleFill: '#e6dcbd',
    compositeStroke: '#586e75',
    compositeStrokeWidth: 1.8,
    compositeRadius: 16,
    pseudoStateFill: '#f4cca2',
    pseudoStateStroke: '#cb4b16',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#073642',
    initFill: '#268bd2',
    exitOuterStroke: '#268bd2',
    exitInnerFill: '#268bd2',
    edgeStroke: '#2aa198',
    edgeLabelHalo: '#fdf6e3',
    edgeLabelGuardColor: '#b58900',
    edgeLabelEffectColor: '#657b83',
    canvasFill: 'transparent',
    noteFill: '#fdefb9',
    noteStroke: '#b58900',
    noteFoldFill: '#ecd583',
    chevronBtnFill: 'rgba(253,246,227,0.7)',
    chevronBtnStroke: 'rgba(88,110,117,0.35)',
};

const SOLARIZED_DARK: SvgPalette = {
    leafFill: '#073642',
    leafStroke: '#2aa198',
    leafStrokeWidth: 1.4,
    leafRadius: 10,
    leafShadowAlpha: 0.3,
    compositeFill: '#002b36',
    compositeTitleFill: '#0d4450',
    compositeStroke: '#268bd2',
    compositeStrokeWidth: 1.8,
    compositeRadius: 16,
    pseudoStateFill: '#402919',
    pseudoStateStroke: '#cb4b16',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#eee8d5',
    initFill: '#268bd2',
    exitOuterStroke: '#2aa198',
    exitInnerFill: '#2aa198',
    edgeStroke: '#839496',
    edgeLabelHalo: '#002b36',
    edgeLabelGuardColor: '#b58900',
    edgeLabelEffectColor: '#93a1a1',
    canvasFill: 'transparent',
    noteFill: '#3e3a20',
    noteStroke: '#b58900',
    noteFoldFill: '#5a5230',
    chevronBtnFill: 'rgba(7,54,66,0.65)',
    chevronBtnStroke: 'rgba(131,148,150,0.4)',
};

const DARCULA_LIGHT: SvgPalette = {
    leafFill: '#f8f8f8',
    leafStroke: '#4a6fa5',
    leafStrokeWidth: 1.4,
    leafRadius: 8,
    leafShadowAlpha: 0.18,
    compositeFill: '#ececec',
    compositeTitleFill: '#dcdcdc',
    compositeStroke: '#365880',
    compositeStrokeWidth: 1.8,
    compositeRadius: 12,
    pseudoStateFill: '#fdecc7',
    pseudoStateStroke: '#a68a21',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#1e1e1e',
    initFill: '#365880',
    exitOuterStroke: '#365880',
    exitInnerFill: '#365880',
    edgeStroke: '#6e7b8a',
    edgeLabelHalo: '#f8f8f8',
    edgeLabelGuardColor: '#a68a21',
    edgeLabelEffectColor: '#7a8998',
    canvasFill: 'transparent',
    noteFill: '#fef5d0',
    noteStroke: '#a68a21',
    noteFoldFill: '#ecd583',
    chevronBtnFill: 'rgba(255,255,255,0.6)',
    chevronBtnStroke: 'rgba(54,88,128,0.35)',
};

const DARCULA_DARK: SvgPalette = {
    leafFill: '#3c3f41',
    leafStroke: '#589df6',
    leafStrokeWidth: 1.4,
    leafRadius: 8,
    leafShadowAlpha: 0.36,
    compositeFill: '#2b2d30',
    compositeTitleFill: '#313335',
    compositeStroke: '#589df6',
    compositeStrokeWidth: 1.8,
    compositeRadius: 12,
    pseudoStateFill: '#433629',
    pseudoStateStroke: '#e8a33d',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#dfe1e5',
    initFill: '#589df6',
    exitOuterStroke: '#589df6',
    exitInnerFill: '#589df6',
    edgeStroke: '#6a88b1',
    edgeLabelHalo: '#2b2d30',
    edgeLabelGuardColor: '#e8a33d',
    edgeLabelEffectColor: '#a7aab4',
    canvasFill: 'transparent',
    noteFill: '#4a3a20',
    noteStroke: '#e8a33d',
    noteFoldFill: '#6d5a2e',
    chevronBtnFill: 'rgba(0,0,0,0.4)',
    chevronBtnStroke: 'rgba(88,157,246,0.4)',
};

const PALETTES: Record<PaletteId, PaletteVariants> = {
    default: {light: DEFAULT_LIGHT, dark: DEFAULT_DARK},
    nord: {light: NORD_LIGHT, dark: NORD_DARK},
    solarized: {light: SOLARIZED_LIGHT, dark: SOLARIZED_DARK},
    darcula: {light: DARCULA_LIGHT, dark: DARCULA_DARK},
};

export const PALETTE_IDS: PaletteId[] = ['default', 'nord', 'solarized', 'darcula'];

export const PALETTE_LABEL: Record<PaletteId, string> = {
    default: 'Default',
    nord: 'Nord',
    solarized: 'Solarized',
    darcula: 'Darcula',
};

export function resolvePalette(id: PaletteId, mode: PaletteMode): SvgPalette {
    const variants = PALETTES[id] || PALETTES.default;
    return variants[mode];
}
