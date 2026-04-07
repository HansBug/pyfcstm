import * as py from './support';

py.runPyAlignmentCases('jsfcstm AST pyfcstm alignment: forced transitions', [
    {
        name: 'state scoped forced transitions',
        text: py.lines(
            'state Root {',
            '    state StateA;',
            '    state StateB;',
            '    !StateA -> StateB;',
            '    !StateA -> StateB :: fromId;',
            '    !StateA -> StateB : chain.id;',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('StateA'),
                py.state('StateB'),
            ],
            force_transitions: [
                py.forceTransition('StateA', 'StateB'),
                py.forceTransition('StateA', 'StateB', {
                    event_id: py.chain(['StateA', 'fromId']),
                }),
                py.forceTransition('StateA', 'StateB', {
                    event_id: py.chain(['chain', 'id']),
                }),
            ],
        })),
    },
    {
        name: 'state scoped forced exit transitions',
        text: py.lines(
            'state Root {',
            '    state StateA;',
            '    !StateA -> [*];',
            '    !StateA -> [*] :: fromId;',
            '    !StateA -> [*] : if [x == 10];',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('StateA'),
            ],
            force_transitions: [
                py.forceTransition('StateA', py.EXIT_STATE),
                py.forceTransition('StateA', py.EXIT_STATE, {
                    event_id: py.chain(['StateA', 'fromId']),
                }),
                py.forceTransition('StateA', py.EXIT_STATE, {
                    condition_expr: py.binary(py.nameExpr('x'), '==', py.intLiteral('10')),
                }),
            ],
        })),
    },
    {
        name: 'all source forced transitions',
        text: py.lines(
            'state Root {',
            '    state StateB;',
            '    !* -> StateB;',
            '    !* -> StateB :: fromId;',
            '    !* -> StateB : chain.id;',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('StateB'),
            ],
            force_transitions: [
                py.forceTransition(py.ALL, 'StateB'),
                py.forceTransition(py.ALL, 'StateB', {
                    event_id: py.chain(['fromId']),
                }),
                py.forceTransition(py.ALL, 'StateB', {
                    event_id: py.chain(['chain', 'id']),
                }),
            ],
        })),
    },
    {
        name: 'all source forced exit and conditional expressions',
        text: py.lines(
            'state Root {',
            '    !* -> [*];',
            '    !* -> [*] :: fromId;',
            '    !* -> [*] : if [(x > 5) ? true : false];',
            '}'
        ),
        expected: py.program(py.rootState({
            force_transitions: [
                py.forceTransition(py.ALL, py.EXIT_STATE),
                py.forceTransition(py.ALL, py.EXIT_STATE, {
                    event_id: py.chain(['fromId']),
                }),
                py.forceTransition(py.ALL, py.EXIT_STATE, {
                    condition_expr: py.conditional(
                        py.binary(py.nameExpr('x'), '>', py.intLiteral('5')),
                        py.boolLiteral('true'),
                        py.boolLiteral('false')
                    ),
                }),
            ],
        })),
    },
    {
        name: 'forced transition boolean aliases align with pyfcstm',
        text: py.lines(
            'state Root {',
            '    state StateA;',
            '    state SafeMode;',
            '    !StateA -> [*] : if [x == 5 || y != 10];',
            '    !* -> SafeMode : if [flag == 0 and x > 10];',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('StateA'),
                py.state('SafeMode'),
            ],
            force_transitions: [
                py.forceTransition('StateA', py.EXIT_STATE, {
                    condition_expr: py.binary(
                        py.binary(py.nameExpr('x'), '==', py.intLiteral('5')),
                        '||',
                        py.binary(py.nameExpr('y'), '!=', py.intLiteral('10'))
                    ),
                }),
                py.forceTransition(py.ALL, 'SafeMode', {
                    condition_expr: py.binary(
                        py.binary(py.nameExpr('flag'), '==', py.intLiteral('0')),
                        '&&',
                        py.binary(py.nameExpr('x'), '>', py.intLiteral('10'))
                    ),
                }),
            ],
        })),
    },
]);
