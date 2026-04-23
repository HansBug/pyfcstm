import * as py from './support';

py.runPyAlignmentCases('jsfcstm AST pyfcstm alignment: imports', [
    {
        name: 'simple imports without mappings',
        text: py.lines(
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '    import "./motor.fcstm" as Motor named "Left Motor";',
            '}'
        ),
        expected: py.program(py.rootState({
            imports: [
                py.importStatement('./worker.fcstm', 'Worker'),
                py.importStatement('./motor.fcstm', 'Motor', [], 'Left Motor'),
            ],
        })),
    },
    {
        name: 'exact variable and relative event import mappings',
        text: py.lines(
            'state Root {',
            '    import "./motor.fcstm" as Motor named "Left Motor" {',
            '        def counter -> left_counter;',
            '        event /Start -> Start named "Motor Start";',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            imports: [
                py.importStatement('./motor.fcstm', 'Motor', [
                    py.importDefMapping(
                        py.importDefExactSelector('counter'),
                        'left_counter'
                    ),
                    py.importEventMapping(
                        py.chain(['Start'], true),
                        py.chain(['Start']),
                        'Motor Start'
                    ),
                ], 'Left Motor'),
            ],
        })),
    },
    {
        name: 'set pattern fallback and absolute event target mappings',
        text: py.lines(
            'state Root {',
            '    import "./pair.fcstm" as Pair {',
            '        def {a, b, c} -> pair_*;',
            '        def a_*_b_* -> pair_${1}_${2};',
            '        def * -> pair_$0;',
            '        event /Stop -> /System.Stop;',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            imports: [
                py.importStatement('./pair.fcstm', 'Pair', [
                    py.importDefMapping(
                        py.importDefSetSelector(['a', 'b', 'c']),
                        'pair_*'
                    ),
                    py.importDefMapping(
                        py.importDefPatternSelector('a_*_b_*'),
                        'pair_${1}_${2}'
                    ),
                    py.importDefMapping(
                        py.importDefFallbackSelector(),
                        'pair_$0'
                    ),
                    py.importEventMapping(
                        py.chain(['Stop'], true),
                        py.chain(['System', 'Stop'], true)
                    ),
                ]),
            ],
        })),
    },
    {
        name: 'complex import block keeps empty statements out of py snapshot',
        text: py.lines(
            'state Root {',
            '    import "./complex.fcstm" as Complex named "Complex Module" {',
            '        ;',
            '        def sensor_* -> io_$1;',
            '        ;',
            '        def x_*_y_*_z_* -> xyz_${1}_${2}_${3};',
            '        event /Start -> Start;',
            '        ;',
            '        event /Reset -> /Plant.Reset named "Plant Reset";',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            imports: [
                py.importStatement('./complex.fcstm', 'Complex', [
                    py.importDefMapping(
                        py.importDefPatternSelector('sensor_*'),
                        'io_$1'
                    ),
                    py.importDefMapping(
                        py.importDefPatternSelector('x_*_y_*_z_*'),
                        'xyz_${1}_${2}_${3}'
                    ),
                    py.importEventMapping(
                        py.chain(['Start'], true),
                        py.chain(['Start'])
                    ),
                    py.importEventMapping(
                        py.chain(['Reset'], true),
                        py.chain(['Plant', 'Reset'], true),
                        'Plant Reset'
                    ),
                ], 'Complex Module'),
            ],
        })),
    },
    {
        name: 'event only import mappings',
        text: py.lines(
            'state Root {',
            '    import "./events.fcstm" as Events {',
            '        event /Start -> Start;',
            '        event /Reset -> /Plant.Reset named "Plant Reset";',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            imports: [
                py.importStatement('./events.fcstm', 'Events', [
                    py.importEventMapping(
                        py.chain(['Start'], true),
                        py.chain(['Start'])
                    ),
                    py.importEventMapping(
                        py.chain(['Reset'], true),
                        py.chain(['Plant', 'Reset'], true),
                        'Plant Reset'
                    ),
                ]),
            ],
        })),
    },
]);
