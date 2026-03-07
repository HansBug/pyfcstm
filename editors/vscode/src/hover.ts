/**
 * FCSTM Hover Provider
 *
 * This module provides hover documentation for FCSTM constructs including:
 * - Event scoping operators (::, :, /)
 * - Pseudo-state marker ([*])
 * - Keywords (pseudo, effect, abstract, ref, etc.)
 * - Lifecycle aspects (during before/after, >> during before/after)
 */

import * as vscode from 'vscode';

/**
 * Hover documentation for FCSTM constructs
 */
const HOVER_DOCS: Record<string, { title: string; description: string; example?: string }> = {
    '::': {
        title: 'Local Event Scope',
        description: 'Creates an event scoped to the source state. Each source state gets its own event instance.',
        example: '```fcstm\nStateA -> StateB :: LocalEvent;\n// Event: Parent.StateA.LocalEvent\n```'
    },
    ':': {
        title: 'Chain Event Scope',
        description: 'References an event scoped to the parent state. Multiple transitions in the same scope share the event.',
        example: '```fcstm\nStateA -> StateB : ChainEvent;\n// Event: Parent.ChainEvent\n```'
    },
    '/': {
        title: 'Absolute Event Scope',
        description: 'References an event scoped to the root state. All transitions using the same absolute path share the event.',
        example: '```fcstm\nStateA -> StateB : /GlobalEvent;\n// Event: Root.GlobalEvent\n```'
    },
    '[*]': {
        title: 'Pseudo-State Marker',
        description: 'Represents a pseudo-state for initial or final transitions. Used for entry and exit points.',
        example: '```fcstm\n[*] -> InitialState;  // Entry transition\nFinalState -> [*];    // Exit transition\n```'
    },
    'pseudo': {
        title: 'Pseudo State',
        description: 'Declares a pseudo state that skips ancestor aspect actions. Useful for junction or choice states.',
        example: '```fcstm\npseudo state Junction;\n```'
    },
    'effect': {
        title: 'Transition Effect',
        description: 'Defines operations to execute when a transition is taken. Effects run after exit actions and before enter actions.',
        example: '```fcstm\nStateA -> StateB effect {\n    counter = counter + 1;\n};\n```'
    },
    'abstract': {
        title: 'Abstract Action',
        description: 'Declares a function that must be implemented in the generated code framework. Used for platform-specific operations.',
        example: '```fcstm\nenter abstract InitializeHardware;\nexit abstract Cleanup;\n```'
    },
    'ref': {
        title: 'Reference Action',
        description: 'Reuses a lifecycle action from another state. Can reference actions using relative or absolute paths.',
        example: '```fcstm\nenter ref StateA.UserInit;\nexit ref /GlobalCleanup;\n```'
    },
    'during before': {
        title: 'During Before Aspect',
        description: 'For composite states: executes before entering child states. For leaf states: not applicable.',
        example: '```fcstm\nstate Parent {\n    during before {\n        // Runs before child enter\n    }\n    state Child;\n}\n```'
    },
    'during after': {
        title: 'During After Aspect',
        description: 'For composite states: executes after exiting child states. For leaf states: not applicable.',
        example: '```fcstm\nstate Parent {\n    during after {\n        // Runs after child exit\n    }\n    state Child;\n}\n```'
    },
    '>> during before': {
        title: 'Global During Before Aspect',
        description: 'Executes before the during action of all descendant leaf states. Applies recursively to nested states.',
        example: '```fcstm\nstate Root {\n    >> during before {\n        // Runs for ALL leaf states\n    }\n    state Child;\n}\n```'
    },
    '>> during after': {
        title: 'Global During After Aspect',
        description: 'Executes after the during action of all descendant leaf states. Applies recursively to nested states.',
        example: '```fcstm\nstate Root {\n    >> during after {\n        // Runs for ALL leaf states\n    }\n    state Child;\n}\n```'
    },
    'named': {
        title: 'Display Name',
        description: 'Provides a human-readable display name for states or events. Used in documentation and visualization.',
        example: '```fcstm\nstate Running named "System Running";\nevent Start named "Start Event";\n```'
    },
    'enter': {
        title: 'Enter Action',
        description: 'Executes when entering a state. Runs after transition effects and before during actions.',
        example: '```fcstm\nstate Active {\n    enter {\n        counter = 0;\n    }\n}\n```'
    },
    'during': {
        title: 'During Action',
        description: 'For leaf states: executes every cycle while the state is active. For composite states: requires before/after aspect.',
        example: '```fcstm\nstate Active {\n    during {\n        counter = counter + 1;\n    }\n}\n```'
    },
    'exit': {
        title: 'Exit Action',
        description: 'Executes when leaving a state. Runs before transition effects and after during actions.',
        example: '```fcstm\nstate Active {\n    exit {\n        counter = 0;\n    }\n}\n```'
    },
    'before': {
        title: 'Before Aspect',
        description: 'Modifier for during actions in composite states. Executes before child state actions.',
        example: '```fcstm\nstate Parent {\n    during before { }\n    state Child;\n}\n```'
    },
    'after': {
        title: 'After Aspect',
        description: 'Modifier for during actions in composite states. Executes after child state actions.',
        example: '```fcstm\nstate Parent {\n    during after { }\n    state Child;\n}\n```'
    },
    'if': {
        title: 'Guard Condition',
        description: 'Specifies a condition that must be true for a transition to be taken. Evaluated at runtime.',
        example: '```fcstm\nStateA -> StateB : if [counter >= 10];\n```'
    },
    'def': {
        title: 'Variable Definition',
        description: 'Defines a state machine variable with a type and initial value. Variables must be defined before states.',
        example: '```fcstm\ndef int counter = 0;\ndef float temperature = 25.5;\n```'
    },
    'state': {
        title: 'State Definition',
        description: 'Defines a state in the state machine. Can be a leaf state (no children) or composite state (with children).',
        example: '```fcstm\nstate Idle;  // Leaf state\nstate Active {  // Composite state\n    state Running;\n}\n```'
    },
    'event': {
        title: 'Event Definition',
        description: 'Explicitly defines an event within a state scope. Events can have display names for documentation.',
        example: '```fcstm\nevent Start;\nevent Stop named "Stop Event";\n```'
    }
};

/**
 * Hover provider for FCSTM documents
 */
export class FcstmHoverProvider implements vscode.HoverProvider {
    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
        _token: vscode.CancellationToken
    ): vscode.Hover | null {
        const line = document.lineAt(position.line);
        const text = line.text;

        // Get word range at position
        const wordRange = document.getWordRangeAtPosition(position);
        const word = wordRange ? document.getText(wordRange) : '';

        // Check for multi-character operators and keywords
        const hoverInfo = this.findHoverInfo(text, position.character, word);

        if (hoverInfo) {
            const markdown = new vscode.MarkdownString();
            markdown.appendMarkdown(`**${hoverInfo.title}**\n\n`);
            markdown.appendMarkdown(`${hoverInfo.description}\n\n`);

            if (hoverInfo.example) {
                markdown.appendMarkdown(`**Example:**\n\n${hoverInfo.example}`);
            }

            return new vscode.Hover(markdown);
        }

        return null;
    }

    /**
     * Find hover information for the position
     */
    private findHoverInfo(
        text: string,
        column: number,
        word: string
    ): { title: string; description: string; example?: string } | null {
        // Check for multi-character operators
        const operators = ['::', '>> during before', '>> during after', 'during before', 'during after'];

        for (const op of operators) {
            const index = this.findOperatorAtPosition(text, column, op);
            if (index !== -1) {
                return HOVER_DOCS[op] || null;
            }
        }

        // Check for single-character operators
        if (column > 0 && column < text.length) {
            const char = text[column];
            const prevChar = text[column - 1];
            const nextChar = text[column + 1];

            // Check for :: (but not just :)
            if (char === ':' && prevChar === ':') {
                return HOVER_DOCS['::'];
            }
            if (char === ':' && nextChar === ':') {
                return HOVER_DOCS['::'];
            }

            // Check for : (chain event)
            if (char === ':' && prevChar !== ':' && nextChar !== ':') {
                // Make sure it's not part of a ternary operator
                if (prevChar !== ')' && nextChar !== ' ') {
                    return HOVER_DOCS[':'];
                }
            }

            // Check for / (absolute event)
            if (char === '/') {
                // Make sure it's not a comment
                if (prevChar !== '/' && nextChar !== '/' && nextChar !== '*') {
                    return HOVER_DOCS['/'];
                }
            }
        }

        // Check for [*]
        if (text.includes('[*]')) {
            const bracketIndex = text.indexOf('[*]');
            if (column >= bracketIndex && column <= bracketIndex + 2) {
                return HOVER_DOCS['[*]'];
            }
        }

        // Check for keywords
        if (word && HOVER_DOCS[word]) {
            return HOVER_DOCS[word];
        }

        return null;
    }

    /**
     * Find operator at position
     */
    private findOperatorAtPosition(text: string, column: number, operator: string): number {
        let index = 0;
        while ((index = text.indexOf(operator, index)) !== -1) {
            if (column >= index && column < index + operator.length) {
                return index;
            }
            index++;
        }
        return -1;
    }
}
