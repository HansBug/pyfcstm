const { FcstmParser } = require('../out/parser');

const GREEN = '\u001b[32m';
const RED = '\u001b[31m';
const CYAN = '\u001b[36m';
const YELLOW = '\u001b[33m';
const RESET = '\u001b[0m';

class ValidationCheckpoint {
    constructor(id, name, description, code, expectedSuccess, expectedMessage = null) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.code = code;
        this.expectedSuccess = expectedSuccess;
        this.expectedMessage = expectedMessage;
    }
}

const CHECKPOINTS = [
    new ValidationCheckpoint('P0.2-01', 'Minimal root state', 'Parse a minimal state machine with one root state.', `state System;`, true),
    new ValidationCheckpoint('P0.2-02', 'Variable definitions', 'Parse int, float, and hex variable definitions before the root state.', `def int counter = 0;\ndef int flags = 0xFF;\ndef float temperature = 25.5;\nstate System;`, true),
    new ValidationCheckpoint('P0.2-03', 'Named leaf state', 'Parse a named leaf state declaration.', `state System named "System Root";`, true),
    new ValidationCheckpoint('P0.2-04', 'Composite state', 'Parse a composite state with nested states and an initial transition.', `state System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-05', 'Event declarations', 'Parse simple and named event declarations inside a state.', `state System {\n    event Start;\n    event Stop named "Stop Event";\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-06', 'Local event transition', 'Parse a transition using local event syntax with ::.', `state System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n    Idle -> Running :: Start;\n}`, true),
    new ValidationCheckpoint('P0.2-07', 'Chain event transition', 'Parse a transition using parent-scoped event syntax with :.', `state System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n    Idle -> Running : Start;\n}`, true),
    new ValidationCheckpoint('P0.2-08', 'Guarded transition', 'Parse a transition with a numeric comparison guard.', `def int counter = 0;\nstate System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n    Idle -> Running : if [counter >= 10];\n}`, true),
    new ValidationCheckpoint('P0.2-09', 'Effect transition', 'Parse a transition with an effect block.', `def int counter = 0;\nstate System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n    Idle -> Running :: Start effect {\n        counter = counter + 1;\n    }\n}`, true),
    new ValidationCheckpoint('P0.2-10', 'Enter block', 'Parse an enter operation block.', `def int counter = 0;\nstate System {\n    enter {\n        counter = 0;\n    }\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-11', 'During before block', 'Parse a during before operation block.', `def int counter = 0;\nstate System {\n    during before {\n        counter = counter + 1;\n    }\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-12', 'During after block', 'Parse a during after operation block.', `def int counter = 0;\nstate System {\n    during after {\n        counter = counter + 1;\n    }\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-13', 'Exit block', 'Parse an exit operation block.', `def int counter = 0;\nstate System {\n    exit {\n        counter = 0;\n    }\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-14', 'Aspect before block', 'Parse a root-level >> during before aspect block.', `def int counter = 0;\nstate System {\n    >> during before {\n        counter = counter + 1;\n    }\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-15', 'Aspect after block', 'Parse a root-level >> during after aspect block.', `def int counter = 0;\nstate System {\n    >> during after {\n        counter = counter + 1;\n    }\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-16', 'Abstract enter action', 'Parse an abstract enter action declaration.', `state System {\n    enter abstract InitHardware;\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-17', 'Reference exit action', 'Parse an exit ref action declaration.', `state System {\n    exit ref /GlobalCleanup;\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-18', 'Pseudo state declaration', 'Parse a pseudo state inside a composite state.', `state System {\n    pseudo state Junction;\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-19', 'Nested composite states', 'Parse nested composite states and inner transitions.', `state System {\n    state Running {\n        state Active;\n        state Waiting;\n        [*] -> Active;\n        Active -> Waiting :: Pause;\n    }\n    [*] -> Running;\n}`, true),
    new ValidationCheckpoint('P0.2-20', 'Forced transition', 'Parse a forced transition from one state.', `state System {\n    state Running;\n    state Error;\n    [*] -> Running;\n    !Running -> Error :: FatalError;\n}`, true),
    new ValidationCheckpoint('P0.2-21', 'Wildcard forced transition', 'Parse a wildcard forced transition from all substates.', `state System {\n    state Running {\n        state Active;\n        [*] -> Active;\n    }\n    state Error;\n    [*] -> Running;\n    !* -> Error :: GlobalError;\n}`, true),
    new ValidationCheckpoint('P0.2-22', 'Math functions and ternary', 'Parse built-in math functions and ternary expressions in operations.', `def int counter = 0;\ndef float temperature = 25.0;\nstate System {\n    during {\n        temperature = sqrt(temperature);\n        counter = (temperature > 10.0) ? 1 : 0;\n    }\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-23', 'Logical guards', 'Parse logical operators in a guard expression.', `def int counter = 0;\ndef float temperature = 25.0;\nstate System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n    Idle -> Running : if [(counter > 10) && (temperature < 30.0)];\n}`, true),
    new ValidationCheckpoint('P0.2-24', 'Absolute ref path', 'Parse absolute reference paths in ref actions.', `state System {\n    during before ref /System.Shared.PreProcess;\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-25', 'Multiline abstract documentation', 'Parse abstract actions with multiline documentation comments.', `state System {\n    enter abstract InitDoc /*\n        Initialize system resources\n        before entering the first state\n    */\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-26', 'Named composite state', 'Parse a named composite root state.', `state System named "Main System" {\n    state Idle;\n    [*] -> Idle;\n}`, true),
    new ValidationCheckpoint('P0.2-27', 'Missing semicolon after def', 'Reject a missing semicolon after variable definition.', `def int counter = 0\nstate System {\n    state Idle;\n    [*] -> Idle;\n}`, false, /semicolon/i),
    new ValidationCheckpoint('P0.2-28', 'Missing semicolon after state', 'Reject a missing semicolon after a leaf state definition.', `state System {\n    state Idle\n    [*] -> Idle;\n}`, false, /semicolon/i),
    new ValidationCheckpoint('P0.2-29', 'Missing closing brace', 'Reject an unclosed composite state block.', `state System {\n    state Idle;\n    [*] -> Idle;\n`, false, /closing brace|Missing closing brace|Unexpected end of file/i),
    new ValidationCheckpoint('P0.2-30', 'Bad transition operator', 'Reject an invalid transition operator.', `state System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n    Idle => Running;\n}`, false, /Invalid operator|Invalid syntax|Unexpected token/i),
    new ValidationCheckpoint('P0.2-31', 'Malformed guard brackets', 'Reject a malformed guard condition missing closing bracket.', `def int counter = 0;\nstate System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n    Idle -> Running : if [counter > 0;\n}`, false, /bracket|Invalid syntax|Unexpected token/i),
    new ValidationCheckpoint('P0.2-32', 'Missing effect block brace', 'Reject an effect block with a missing closing brace.', `def int counter = 0;\nstate System {\n    state Idle;\n    state Running;\n    [*] -> Idle;\n    Idle -> Running :: Start effect {\n        counter = counter + 1;\n}`, false, /closing brace|Missing closing brace|Unexpected end of file/i)
];

function colorize(color, text) {
    return `${color}${text}${RESET}`;
}

function formatErrors(errors) {
    if (!errors || !errors.length) {
        return '  (no parser errors returned)';
    }

    return errors
        .map((error, index) => `  ${index + 1}. line=${error.line}, column=${error.column}, severity=${error.severity}\n     ${error.message}`)
        .join('\n');
}

async function runCheckpoint(parser, checkpoint, index, total) {
    const result = await parser.parse(checkpoint.code);
    const label = `[${index + 1}/${total}] ${checkpoint.id} ${checkpoint.name} - ${checkpoint.description}`;
    const messageMatched = checkpoint.expectedMessage
        ? result.errors.some((item) => checkpoint.expectedMessage.test(item.message))
        : true;
    const passed = checkpoint.expectedSuccess
        ? result.success === true && result.errors.length === 0
        : result.success === false && result.errors.length > 0 && messageMatched;

    if (passed) {
        console.log(`${colorize(GREEN, '✅')} ${label}`);
        return true;
    }

    console.log(`${colorize(RED, '❌')} ${label}`);
    console.log(colorize(YELLOW, '  Expected:'));
    console.log(`  success=${checkpoint.expectedSuccess}${checkpoint.expectedMessage ? `, error~=${checkpoint.expectedMessage}` : ''}`);
    console.log(colorize(YELLOW, '  Actual result:'));
    console.log(`  success=${result.success}, errors=${result.errors.length}`);
    console.log(colorize(YELLOW, '  Error details:'));
    console.log(formatErrors(result.errors));
    console.log(colorize(YELLOW, '  Source snippet:'));
    console.log(checkpoint.code.split('\n').map((line, lineIndex) => `    ${String(lineIndex + 1).padStart(2, '0')}: ${line}`).join('\n'));
    return false;
}

async function run() {
    console.log(colorize(CYAN, 'FCSTM VSCode P0.2 Comprehensive Verification'));
    console.log(colorize(CYAN, '================================================'));

    const parser = new FcstmParser();
    const total = CHECKPOINTS.length;
    let passedCount = 0;

    for (let i = 0; i < CHECKPOINTS.length; i++) {
        const passed = await runCheckpoint(parser, CHECKPOINTS[i], i, total);
        if (passed) {
            passedCount += 1;
        }
    }

    console.log('');
    console.log(colorize(CYAN, 'Summary'));
    console.log(colorize(CYAN, '-------'));
    console.log(`Total checkpoints: ${total}`);
    console.log(`Passed: ${passedCount}`);
    console.log(`Failed: ${total - passedCount}`);

    if (passedCount !== total) {
        process.exit(1);
    }

    console.log(colorize(GREEN, 'All P0.2 verification checkpoints passed.'));
}

run().catch((err) => {
    console.error(`${colorize(RED, '❌')} P0.2 verification script crashed.`);
    console.error(err && err.stack ? err.stack : err);
    process.exit(1);
});
