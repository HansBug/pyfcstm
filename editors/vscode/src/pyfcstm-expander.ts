/*
 * Outline a diagram's text using an installed `pyfcstm`.
 *
 * The preview webview has the drawing on screen but no fonts to outline it
 * with, so its SVG download depends on text the reader may not have installed.
 * Shipping the outliner would mean adding resvg and the CJK faces to the
 * extension -- 17.7 MB for one locale, 59.4 MB for all of them -- so instead
 * this asks a `pyfcstm[viz]` that is already on the machine.
 *
 * It expands the document the webview produced rather than re-rendering from
 * the `.fcstm` source. Re-rendering would return a valid file in the default
 * palette, discarding the palette and colour mode the user picked: a
 * wrong-colour export that looks entirely well-formed.
 *
 * When nothing suitable is installed the caller is told so. That is the whole
 * contract -- there is no silent fallback to an unexpanded document, because
 * handing over a file that renders differently on the reader's machine is the
 * failure this exists to prevent.
 */
import {execFile} from 'child_process';
import {mkdtemp, readFile, rm, writeFile} from 'fs/promises';
import {tmpdir} from 'os';
import {join} from 'path';
import * as vscode from 'vscode';

/** How long a single expansion may take before it is abandoned. */
const EXPAND_TIMEOUT_MS = 60_000;

/** How long the one-time probe for a usable command may take. */
const PROBE_TIMEOUT_MS = 20_000;

/**
 * Largest expanded document accepted from the subprocess, in bytes.
 *
 * The same ceiling the Python export enforces. Reading an unbounded amount from
 * a child process into the extension host is the one way this can hurt the
 * editor rather than merely fail.
 */
const MAX_EXPANDED_BYTES = 67_108_864;

/** Command words to try, in order, when the setting names nothing. */
const CANDIDATE_COMMANDS: ReadonlyArray<ReadonlyArray<string>> = [
    ['pyfcstm'],
    ['python3', '-m', 'pyfcstm'],
    ['python', '-m', 'pyfcstm'],
];

interface RunResult {
    code: number;
    stdout: string;
    stderr: string;
}

function run(command: ReadonlyArray<string>, args: string[], timeout: number): Promise<RunResult> {
    return new Promise(resolve => {
        execFile(
            command[0],
            [...command.slice(1), ...args],
            {timeout, maxBuffer: MAX_EXPANDED_BYTES, windowsHide: true},
            (error, stdout, stderr) => {
                if (!error) {
                    resolve({code: 0, stdout, stderr});
                    return;
                }
                // `execFile` reports a missing executable, a non-zero exit and a
                // timeout through the same callback, and all three mean the same
                // thing here: this candidate cannot do the work. Anything with no
                // recognisable shape is surfaced as a failure too rather than
                // being mistaken for success.
                const code = typeof (error as {code?: unknown}).code === 'number'
                    ? (error as {code: number}).code
                    : 1;
                resolve({code: code || 1, stdout: String(stdout || ''), stderr: String(stderr || error.message)});
            },
        );
    });
}

/**
 * The command this host will use, or `null` with the reason it found none.
 *
 * Resolved once and remembered: probing three candidates on every export would
 * add a subprocess launch to each download for no new information.
 */
export interface ExpanderResolution {
    command: ReadonlyArray<string> | null;
    detail: string;
}

let cached: ExpanderResolution | undefined;

function configuredCommand(): ReadonlyArray<string> | null {
    const raw = vscode.workspace.getConfiguration('fcstm').get<string>('diagram.pyfcstmPath');
    const text = typeof raw === 'string' ? raw.trim() : '';
    if (!text) return null;
    // A setting is an explicit choice, so it is used or reported, never quietly
    // replaced by a guess from the candidate list.
    return [text];
}

/**
 * Find a `pyfcstm` that can expand, probing each candidate once.
 *
 * The probe runs `expand-svg --help` rather than checking a version string: an
 * older release on the PATH has the executable but not the command, and the
 * question being asked is whether this one can do the work.
 */
export async function resolveExpander(force = false): Promise<ExpanderResolution> {
    if (cached && !force) return cached;
    const explicit = configuredCommand();
    const candidates = explicit ? [explicit] : CANDIDATE_COMMANDS;
    const tried: string[] = [];
    for (const candidate of candidates) {
        const result = await run(candidate, ['expand-svg', '--help'], PROBE_TIMEOUT_MS);
        if (result.code === 0) {
            cached = {command: candidate, detail: candidate.join(' ')};
            return cached;
        }
        tried.push(`${candidate.join(' ')}: ${(result.stderr || '').trim().split('\n')[0] || `exit ${result.code}`}`);
    }
    cached = {
        command: null,
        detail: explicit
            ? `fcstm.diagram.pyfcstmPath is set but cannot expand — ${tried[0]}`
            : `no installed pyfcstm with expand-svg was found (tried ${tried.join('; ')})`,
    };
    return cached;
}

/**
 * The most recent expansion, so one export does not pay for three.
 *
 * A single download expands the same document up to three times -- once for the
 * SVG, once for the raster the PNG comes from, and once inside the PDF writer.
 * Until this host had an expander those calls returned their input unchanged and
 * cost nothing; now each one is a subprocess, a resvg start-up and a temporary
 * directory. Keyed by the document itself, because that is exactly what decides
 * the answer.
 *
 * One entry: the three calls in an export carry the same string, and holding
 * more would keep whole documents alive for a hit that does not happen.
 */
let lastExpansion: {key: string; promise: Promise<string>} | undefined;

/** Forget the resolution and the cached expansion, so the next request redoes both. */
export function resetExpander(): void {
    cached = undefined;
    lastExpansion = undefined;
}

/**
 * Expand one canonical SVG, or throw with what went wrong.
 *
 * Files rather than pipes: the document routinely runs to tens of kilobytes and
 * an SVG on a command line would meet the platform's argument limit long before
 * that, in a way that depends on the diagram.
 */
export function expandSvg(svg: string): Promise<string> {
    if (lastExpansion && lastExpansion.key === svg) return lastExpansion.promise;
    const promise = runExpansion(svg);
    lastExpansion = {key: svg, promise};
    // A failure is not cached: the reason is usually about the environment -- no
    // interpreter yet, a renderer that ran out of memory -- and a caller retrying
    // after fixing it would otherwise get the old error back.
    promise.catch(() => {
        // Identity, not the key: after a reset a new promise can be in the cache
        // under the same document, and clearing by key would drop that one when
        // this older attempt finally fails -- costing a re-run for no reason.
        if (lastExpansion && lastExpansion.promise === promise) lastExpansion = undefined;
    });
    return promise;
}

async function runExpansion(svg: string): Promise<string> {
    const resolution = await resolveExpander();
    if (!resolution.command) {
        throw new Error(resolution.detail);
    }
    const directory = await mkdtemp(join(tmpdir(), 'pyfcstm-expand-'));
    const input = join(directory, 'canonical.svg');
    const output = join(directory, 'expanded.svg');
    try {
        await writeFile(input, svg, 'utf8');
        const result = await run(
            resolution.command,
            ['expand-svg', '-i', input, '-o', output],
            EXPAND_TIMEOUT_MS,
        );
        if (result.code !== 0) {
            throw new Error(
                `${resolution.detail} could not expand the diagram: `
                + `${(result.stderr || result.stdout || '').trim().split('\n').slice(-1)[0] || `exit ${result.code}`}`,
            );
        }
        const expanded = await readFile(output, 'utf8');
        if (!expanded.includes('<svg')) {
            throw new Error(`${resolution.detail} produced something that is not an SVG document`);
        }
        return expanded;
    } finally {
        // A left-behind temporary holding the user's diagram is worse than a
        // failed cleanup, so removal is unconditional; its own failure is
        // reported rather than dropped.
        await rm(directory, {recursive: true, force: true}).catch((error: unknown) => {
            console.warn(`pyfcstm expander could not remove ${directory}: ${String(error)}`);
        });
    }
}
