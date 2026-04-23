import * as py from './support';

py.runPyAlignmentCases('jsfcstm AST pyfcstm alignment: states and events', [
    {
        name: 'leaf state naming variants',
        text: py.lines(
            'state Machine {',
            '    state S1;',
            '    state Running;',
            '    state IDLE;',
            '    state s_2;',
            '    state waiting_for_input;',
            '}'
        ),
        expected: py.program(py.state('Machine', {
            substates: [
                py.state('S1'),
                py.state('Running'),
                py.state('IDLE'),
                py.state('s_2'),
                py.state('waiting_for_input'),
            ],
        })),
    },
    {
        name: 'named leaf and pseudo states',
        text: py.lines(
            'state Container {',
            '    state idle named "Idle State";',
            '    state running named "Running State";',
            '    pseudo state error named "Error State";',
            '}'
        ),
        expected: py.program(py.state('Container', {
            substates: [
                py.state('idle', {extra_name: 'Idle State'}),
                py.state('running', {extra_name: 'Running State'}),
                py.state('error', {extra_name: 'Error State', is_pseudo: true}),
            ],
        })),
    },
    {
        name: 'named composite states and deep nesting',
        text: py.lines(
            'state outer named "Outer State" {',
            '    state inner named "Inner State" {',
            '        state deep named "Deep State";',
            '    }',
            '}'
        ),
        expected: py.program(py.state('outer', {
            extra_name: 'Outer State',
            substates: [
                py.state('inner', {
                    extra_name: 'Inner State',
                    substates: [
                        py.state('deep', {extra_name: 'Deep State'}),
                    ],
                }),
            ],
        })),
    },
    {
        name: 'pseudo composite with named children',
        text: py.lines(
            'pseudo state root named "Root State" {',
            '    state branch1 named "Branch 1" {}',
            '    state branch2 named "Branch 2" {}',
            '}'
        ),
        expected: py.program(py.state('root', {
            extra_name: 'Root State',
            is_pseudo: true,
            substates: [
                py.state('branch1', {extra_name: 'Branch 1'}),
                py.state('branch2', {extra_name: 'Branch 2'}),
            ],
        })),
    },
    {
        name: 'state machine style nested states and transitions',
        text: py.lines(
            'state Machine {',
            '    state Off;',
            '    state On {',
            '        state Idle;',
            '        state Running;',
            '    }',
            '    Off -> On: if [power == 1];',
            '    On -> Off: if [power == 0];',
            '}'
        ),
        expected: py.program(py.state('Machine', {
            substates: [
                py.state('Off'),
                py.state('On', {
                    substates: [
                        py.state('Idle'),
                        py.state('Running'),
                    ],
                }),
            ],
            transitions: [
                py.transition('Off', 'On', {
                    condition_expr: py.binary(py.nameExpr('power'), '==', py.intLiteral('1')),
                }),
                py.transition('On', 'Off', {
                    condition_expr: py.binary(py.nameExpr('power'), '==', py.intLiteral('0')),
                }),
            ],
        })),
    },
    {
        name: 'state with named workflow children and mixed statements',
        text: py.lines(
            'state WorkflowState named "Main Workflow" {',
            '    enter {',
            '        x = 10;',
            '    }',
            '    state SubState;',
            '    event ProcessComplete named "Processing Completed";',
            '    event ErrorOccurred;',
            '}'
        ),
        expected: py.program(py.state('WorkflowState', {
            extra_name: 'Main Workflow',
            substates: [
                py.state('SubState'),
            ],
            events: [
                py.eventDefinition('ProcessComplete', 'Processing Completed'),
                py.eventDefinition('ErrorOccurred'),
            ],
            enters: [
                py.enterOperations([
                    py.assign('x', py.intLiteral('10')),
                ]),
            ],
        })),
    },
    {
        name: 'named order case keeps category ordering stable',
        text: py.lines(
            'state NamedOrder named "Main" {',
            '    state ChildA named "A";',
            '    event Ev1 named "One";',
            '    state ChildB named "B";',
            '    event Ev2 named "Two";',
            '}'
        ),
        expected: py.program(py.state('NamedOrder', {
            extra_name: 'Main',
            substates: [
                py.state('ChildA', {extra_name: 'A'}),
                py.state('ChildB', {extra_name: 'B'}),
            ],
            events: [
                py.eventDefinition('Ev1', 'One'),
                py.eventDefinition('Ev2', 'Two'),
            ],
        })),
    },
    {
        name: 'event definition naming variants',
        text: py.lines(
            'state Root {',
            '    event myEvent;',
            '    event onClick;',
            '    event button_click;',
            '    event EVENT_NAME;',
            '    event _privateEvent;',
            '    event event123;',
            '    event a;',
            '}'
        ),
        expected: py.program(py.rootState({
            events: [
                py.eventDefinition('myEvent'),
                py.eventDefinition('onClick'),
                py.eventDefinition('button_click'),
                py.eventDefinition('EVENT_NAME'),
                py.eventDefinition('_privateEvent'),
                py.eventDefinition('event123'),
                py.eventDefinition('a'),
            ],
        })),
    },
    {
        name: 'event definitions with named clauses and escapes',
        text: py.lines(
            'state Root {',
            '    event myEvent named "My Event";',
            '    event testEvent named "Event with \\"escaped\\" quotes";',
            '    event fileEvent named "File\\nNew\\tLine";',
            '    event mixedEvent named \'Contains "double" quotes\';',
            '}'
        ),
        expected: py.program(py.rootState({
            events: [
                py.eventDefinition('myEvent', 'My Event'),
                py.eventDefinition('testEvent', 'Event with "escaped" quotes'),
                py.eventDefinition('fileEvent', 'File\nNew\tLine'),
                py.eventDefinition('mixedEvent', 'Contains "double" quotes'),
            ],
        })),
    },
    {
        name: 'event definitions decode unicode hex octal and control escapes',
        text: py.lines(
            'state Root {',
            '    event unicodeEvent named "Greek \\u03A9";',
            '    event hexEvent named "Hex \\x41";',
            '    event octalEvent named "Octal \\101";',
            '    event controlEvent named "Line1\\rLine2\\fPage";',
            '    event slashEvent named "Path \\\\ root";',
            '}'
        ),
        expected: py.program(py.rootState({
            events: [
                py.eventDefinition('unicodeEvent', 'Greek Ω'),
                py.eventDefinition('hexEvent', 'Hex A'),
                py.eventDefinition('octalEvent', 'Octal A'),
                py.eventDefinition('controlEvent', 'Line1\rLine2\fPage'),
                py.eventDefinition('slashEvent', 'Path \\ root'),
            ],
        })),
    },
    {
        name: 'controller events on pseudo state',
        text: py.lines(
            'pseudo state ControllerState {',
            '    event StartEvent;',
            '    event StopEvent named "Stop Operation";',
            '    event ResetEvent named "System Reset";',
            '}'
        ),
        expected: py.program(py.state('ControllerState', {
            is_pseudo: true,
            events: [
                py.eventDefinition('StartEvent'),
                py.eventDefinition('StopEvent', 'Stop Operation'),
                py.eventDefinition('ResetEvent', 'System Reset'),
            ],
        })),
    },
]);
