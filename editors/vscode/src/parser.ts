/**
 * FCSTM Parser Adapter for VSCode Extension
 *
 * This module provides parsing capabilities for FCSTM documents in the VSCode extension.
 *
 * ## Implementation Note: JavaScript Reserved Keyword Conflict
 *
 * The ANTLR grammar (Grammar.g4) uses `function` as a label name in:
 * - Line 112: `function=UFUNC_NAME` in `init_expression`
 * - Line 128: `function=UFUNC_NAME` in `num_expression`
 *
 * This conflicts with JavaScript's reserved `function` keyword, preventing direct
 * JavaScript code generation from ANTLR.
 *
 * ## Current Solution: Python CLI Bridge
 *
 * Instead of generating a JavaScript parser, we use the existing Python parser via
 * subprocess. This approach:
 * - Leverages the battle-tested Python implementation
 * - Maintains single source of truth (no grammar duplication)
 * - Provides reliable parsing with structured error messages
 * - Requires Python runtime (acceptable for development scenarios)
 *
 * ## Future Enhancement Options
 *
 * If pure JavaScript parsing becomes necessary:
 * 1. Create a JavaScript-specific grammar copy with renamed labels
 * 2. Use ANTLR's JavaScript target with the modified grammar
 * 3. Maintain synchronization between Python and JavaScript grammars
 */

import { spawn } from 'child_process';

/**
 * Represents a parse error with location information
 */
export interface ParseError {
    line: number;
    column: number;
    message: string;
    severity: 'error' | 'warning';
}

/**
 * Result of parsing an FCSTM document
 */
export interface ParseResult {
    success: boolean;
    errors: ParseError[];
}

/**
 * Parser adapter for FCSTM documents
 */
export class FcstmParser {
    private pythonPath: string | null = null;
    private pyfcstmAvailable: boolean = false;
    private readonly readyPromise: Promise<void>;

    constructor() {
        this.readyPromise = this.detectPythonEnvironment();
    }

    /**
     * Detect Python environment and pyfcstm availability
     */
    private async detectPythonEnvironment(): Promise<void> {
        try {
            // Try to find Python
            const pythonCandidates = ['python3', 'python'];

            for (const candidate of pythonCandidates) {
                try {
                    const result = await this.runCommand(candidate, ['--version']);
                    if (result.exitCode === 0) {
                        this.pythonPath = candidate;
                        break;
                    }
                } catch {
                    continue;
                }
            }

            if (!this.pythonPath) {
                return;
            }

            // Check if pyfcstm is available
            const result = await this.runCommand(this.pythonPath, ['-m', 'pyfcstm', '--version']);
            this.pyfcstmAvailable = result.exitCode === 0;
        } catch {
            this.pyfcstmAvailable = false;
        }
    }

    /**
     * Run a command and capture output
     */
    private runCommand(command: string, args: string[], input?: string): Promise<{
        exitCode: number;
        stdout: string;
        stderr: string;
    }> {
        return new Promise((resolve) => {
            const proc = spawn(command, args);
            let stdout = '';
            let stderr = '';

            proc.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            proc.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            if (input) {
                proc.stdin.write(input);
                proc.stdin.end();
            }

            proc.on('close', (code) => {
                resolve({
                    exitCode: code || 0,
                    stdout,
                    stderr
                });
            });

            proc.on('error', () => {
                resolve({
                    exitCode: 1,
                    stdout,
                    stderr: stderr || 'Failed to execute command'
                });
            });
        });
    }

    /**
     * Parse FCSTM document text
     *
     * @param text The FCSTM document text to parse
     * @returns Parse result with success status and any errors
     */
    async parse(text: string): Promise<ParseResult> {
        await this.readyPromise;

        if (!this.pyfcstmAvailable || !this.pythonPath) {
            // Fallback: basic syntax checking without full parsing
            return this.basicSyntaxCheck(text);
        }

        try {
            const pythonCode = `
import json
import sys
from pyfcstm.dsl.parse import parse_with_grammar_entry
from pyfcstm.dsl.error import GrammarParseError

text = sys.stdin.read()

try:
    parse_with_grammar_entry(text, "state_machine_dsl")
    print(json.dumps({"success": True, "errors": []}))
except GrammarParseError as err:
    payload = []
    for item in err.errors:
        payload.append({
            "line": max(getattr(item, "line", 1) - 1, 0),
            "column": getattr(item, "column", 0),
            "message": str(item),
            "severity": "error",
        })
    print(json.dumps({"success": False, "errors": payload}))
except Exception as err:
    print(json.dumps({
        "success": False,
        "errors": [{
            "line": 0,
            "column": 0,
            "message": str(err),
            "severity": "error",
        }],
    }))
`.trim();

            const result = await this.runCommand(
                this.pythonPath,
                ['-c', pythonCode],
                text
            );

            if (result.stdout.trim()) {
                const parsed = JSON.parse(result.stdout) as ParseResult;
                return parsed;
            }

            return {
                success: false,
                errors: this.parseErrorOutput(result.stderr)
            };
        } catch (error) {
            return {
                success: false,
                errors: [{
                    line: 0,
                    column: 0,
                    message: `Parser error: ${error}`,
                    severity: 'error'
                }]
            };
        }
    }

    /**
     * Parse error output from Python parser
     */
    private parseErrorOutput(stderr: string): ParseError[] {
        const errors: ParseError[] = [];
        const lines = stderr.split('\n');

        for (const line of lines) {
            // Match common error patterns
            // Example: "line 5:10 mismatched input..."
            const match = line.match(/line (\d+):(\d+)\s+(.+)/i);
            if (match) {
                errors.push({
                    line: parseInt(match[1]) - 1, // VSCode uses 0-based line numbers
                    column: parseInt(match[2]),
                    message: match[3],
                    severity: 'error'
                });
            } else if (line.trim() && !line.startsWith('Traceback')) {
                // Generic error message
                errors.push({
                    line: 0,
                    column: 0,
                    message: line.trim(),
                    severity: 'error'
                });
            }
        }

        return errors;
    }

    /**
     * Basic syntax checking without full parsing
     * This is a fallback when Python parser is not available
     */
    private basicSyntaxCheck(text: string): ParseResult {
        const errors: ParseError[] = [];
        const lines = text.split('\n');

        // Basic checks for common syntax errors
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();

            // Check for unmatched braces
            const openBraces = (line.match(/\{/g) || []).length;
            const closeBraces = (line.match(/\}/g) || []).length;

            if (openBraces !== closeBraces) {
                errors.push({
                    line: i,
                    column: 0,
                    message: 'Unmatched braces',
                    severity: 'warning'
                });
            }
        }

        return {
            success: errors.length === 0,
            errors
        };
    }

    /**
     * Check if the parser is available
     */
    isAvailable(): boolean {
        return this.pyfcstmAvailable;
    }
}

/**
 * Singleton parser instance
 */
let parserInstance: FcstmParser | null = null;

/**
 * Get the parser instance
 */
export function getParser(): FcstmParser {
    if (!parserInstance) {
        parserInstance = new FcstmParser();
    }
    return parserInstance;
}
