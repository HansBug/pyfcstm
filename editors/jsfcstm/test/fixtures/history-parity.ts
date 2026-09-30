// Generated at authoring time from pyfcstm; jsfcstm must reproduce these observations.
export const HISTORY_DIAGNOSTIC_CASES: Record<string, {source: string; expected: Array<{code: string; severity: string; refs: Record<string, string>}>}> = {
    "duplicate": {
        "source": "def int x = 0;\n\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H] -> A; [H] -> A;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_DECLARATION_INVALID",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "shallow",
                    "default": "A",
                    "reason": "duplicate"
                }
            }
        ]
    },
    "default-not-direct-child": {
        "source": "def int x = 0;\n\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H] -> W.W1;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_DECLARATION_INVALID",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "shallow",
                    "default": "W.W1",
                    "reason": "default_not_direct_child"
                }
            },
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "shallow"
                }
            }
        ]
    },
    "default-not-found": {
        "source": "def int x = 0;\n\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H*] -> W.Nope;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H*] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_DECLARATION_INVALID",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep",
                    "default": "W.Nope",
                    "reason": "default_not_found"
                }
            },
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep"
                }
            }
        ]
    },
    "default-through-leaf": {
        "source": "def int x = 0;\n\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H*] -> A.Deeper;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H*] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_DECLARATION_INVALID",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep",
                    "default": "A.Deeper",
                    "reason": "default_not_found"
                }
            },
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep"
                }
            }
        ]
    },
    "default-pseudo": {
        "source": "def int x = 0;\n\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H*] -> P;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H*] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_DECLARATION_INVALID",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep",
                    "default": "P",
                    "reason": "default_pseudo"
                }
            },
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep"
                }
            }
        ]
    },
    "root-owner": {
        "source": "state R { state A; [*] -> A; [H] -> A; }",
        "expected": [
            {
                "code": "E_HISTORY_DECLARATION_INVALID",
                "severity": "error",
                "refs": {
                    "owner_path": "R",
                    "kind": "shallow",
                    "default": "A",
                    "reason": "root_owner"
                }
            }
        ]
    },
    "undeclared-shallow": {
        "source": "state R { state A; state O { state B; [*] -> B; } [*] -> A; A -> O.[H]; }",
        "expected": [
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "shallow"
                }
            }
        ]
    },
    "undeclared-deep": {
        "source": "state R { state A; state O { state B; [*] -> B; [H] -> B; } [*] -> A; A -> O.[H*]; }",
        "expected": [
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep"
                }
            },
            {
                "code": "W_HISTORY_UNUSED",
                "severity": "warning",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "shallow"
                }
            }
        ]
    },
    "undeclared-leaf": {
        "source": "state R { state A; state L; [*] -> A; A -> L.[H]; }",
        "expected": [
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.L",
                    "kind": "shallow"
                }
            }
        ]
    },
    "undeclared-forced": {
        "source": "state R { state A; state O { state B; [*] -> B; } [*] -> A; !A -> O.[H*] :: Go; }",
        "expected": [
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep"
                }
            }
        ]
    },
    "undeclared-all-forced": {
        "source": "state R { state A; state C; state O { state B; [*] -> B; } [*] -> A; !* -> O.[H] :: Go; }",
        "expected": [
            {
                "code": "E_HISTORY_TARGET_UNDECLARED",
                "severity": "error",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "shallow"
                }
            }
        ]
    },
    "unused-both": {
        "source": "state R { state A; state O { state B; [*] -> B; [H] -> B; [H*] -> B; } [*] -> A; A -> O :: Go; }",
        "expected": [
            {
                "code": "W_HISTORY_UNUSED",
                "severity": "warning",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "shallow"
                }
            },
            {
                "code": "W_HISTORY_UNUSED",
                "severity": "warning",
                "refs": {
                    "owner_path": "R.O",
                    "kind": "deep"
                }
            }
        ]
    },
    "reserved-variable": {
        "source": "def int x = 0;\ndef int __hist_x = 0;\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H] -> A;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_RESERVED_PREFIX",
                "severity": "error",
                "refs": {
                    "identifier": "__hist_x",
                    "identifier_kind": "variable"
                }
            }
        ]
    },
    "reserved-single-underscore": {
        "source": "def int x = 0;\ndef int _hist_goto = 0;\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H] -> A;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_RESERVED_PREFIX",
                "severity": "error",
                "refs": {
                    "identifier": "_hist_goto",
                    "identifier_kind": "variable"
                }
            }
        ]
    },
    "reserved-state": {
        "source": "def int x = 0;\n\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H] -> A; state __hist_gate_1;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_RESERVED_PREFIX",
                "severity": "error",
                "refs": {
                    "identifier": "__hist_gate_1",
                    "identifier_kind": "state"
                }
            }
        ]
    },
    "reserved-temporary": {
        "source": "def int x = 0;\n\nstate R {\n    state Off;\n    state O {\n        state A;\n        state W { state W1; state W2; [*] -> W1; }\n        pseudo state P;\n        [*] -> A;\n        [H] -> A; A -> A :: Tick effect { __hist_tmp = 1; x = __hist_tmp; }\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    !O -> Off :: Stop;\n    Off -> O.[H] :: Resume;\n}\n",
        "expected": [
            {
                "code": "E_HISTORY_RESERVED_PREFIX",
                "severity": "error",
                "refs": {
                    "identifier": "__hist_tmp",
                    "identifier_kind": "temporary"
                }
            }
        ]
    },
    "reserved-without-history": {
        "source": "def int __hist_goto = 0; state R { state A; [*] -> A; }",
        "expected": [
            {
                "code": "W_HISTORY_RESERVED_PREFIX",
                "severity": "warning",
                "refs": {
                    "identifier": "__hist_goto",
                    "identifier_kind": "variable"
                }
            }
        ]
    },
    "single-underscore-without-history": {
        "source": "def int _hist_goto = 0; state R { state A; [*] -> A; }",
        "expected": []
    }
};

export const HISTORY_MODEL_CASES: Record<string, {source: string; owners: unknown[]; initial_targets: Record<string, unknown[]>; unconditional_missing: unknown[]}> = {
    "washer": {
        "source": "\ndef int program_entries = 0;\ndef int fill_entries = 0;\ndef int agitate_entries = 0;\ndef int wash_initials = 0;\n\nstate Washer {\n    state Paused;\n    state Program {\n        enter { program_entries = program_entries + 1; }\n        state Idle;\n        state Wash {\n            state Fill {\n                enter { fill_entries = fill_entries + 1; }\n            }\n            state Agitate {\n                enter { agitate_entries = agitate_entries + 1; }\n            }\n            [*] -> Fill effect { wash_initials = wash_initials + 1; }\n            Fill -> Agitate :: Filled;\n        }\n        [*] -> Idle;\n        [H] -> Idle;\n        [H*] -> Wash.Fill;\n        Idle -> Wash :: Start;\n    }\n    [*] -> Paused;\n    Paused -> Program :: Fresh;\n    Paused -> Program.[H] :: Shallow;\n    Paused -> Program.[H*] :: Deep;\n    !Program -> Paused :: Pause;\n}\n",
        "owners": [
            {
                "owner_path": [
                    "Washer",
                    "Program"
                ],
                "record_variable": "__hist_Program",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "shallow": [
                        "Idle"
                    ],
                    "deep": [
                        "Wash",
                        "Fill"
                    ]
                },
                "leaf_ids": {
                    "Idle": 4,
                    "Wash.Fill": 6,
                    "Wash.Agitate": 7
                }
            }
        ],
        "initial_targets": {
            "Washer": [
                {
                    "target": "Washer.Paused",
                    "guard": null,
                    "event": null,
                    "is_unconditional": true
                }
            ],
            "Washer.Program": [
                {
                    "target": "Washer.Program.Wash",
                    "guard": "__hist_goto >= 5 && __hist_goto <= 7",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "Washer.Program.Idle",
                    "guard": "__hist_goto == 0 || __hist_goto == 4",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "merged"
                }
            ],
            "Washer.Program.Wash": [
                {
                    "target": "Washer.Program.Wash.Fill",
                    "guard": "__hist_goto == 6",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "Washer.Program.Wash.Agitate",
                    "guard": "__hist_goto == 7",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "Washer.Program.Wash.Fill",
                    "guard": "__hist_goto == 0 || __hist_goto == 5",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "gated"
                }
            ]
        },
        "unconditional_missing": []
    },
    "blocked-gated": {
        "source": "\ndef int ready = 1;\ndef int fresh_entries = 0;\nstate R {\n    state Off;\n    state O {\n        state Idle;\n        state K {\n            state K1;\n            [*] -> K1 : if [ready == 1];\n        }\n        [*] -> Idle effect { fresh_entries = fresh_entries + 1; }\n        [H] -> Idle;\n        [H*] -> K;\n        Idle -> K :: Go;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    Off -> O.[H] :: Resume;\n    Off -> O.[H*] :: ResumeDeep;\n    !O -> Off :: Stop;\n    Off -> Off :: Block effect { ready = 0; }\n}\n",
        "owners": [
            {
                "owner_path": [
                    "R",
                    "O"
                ],
                "record_variable": "__hist_O",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "shallow": [
                        "Idle"
                    ],
                    "deep": [
                        "K"
                    ]
                },
                "leaf_ids": {
                    "Idle": 4,
                    "K.K1": 6
                }
            }
        ],
        "initial_targets": {
            "R": [
                {
                    "target": "R.Off",
                    "guard": null,
                    "event": null,
                    "is_unconditional": true
                }
            ],
            "R.O": [
                {
                    "target": "R.O.K",
                    "guard": "__hist_goto >= 5 && __hist_goto <= 6",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.O.Idle",
                    "guard": "__hist_goto == 4",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.O.Idle",
                    "guard": "__hist_goto == 0",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "gated"
                }
            ],
            "R.O.K": [
                {
                    "target": "R.O.K.K1",
                    "guard": "(__hist_goto == 0 || __hist_goto == 5) && ready == 1 || __hist_goto == 6",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "merged"
                }
            ]
        },
        "unconditional_missing": [
            {
                "composite_path": "R.O.K",
                "existing_conditional_count": 1,
                "first_child_name": "K1"
            }
        ]
    },
    "blocked-merged": {
        "source": "\ndef int ready = 1;\ndef int fresh_entries = 0;\nstate R {\n    state Off;\n    state O {\n        state Idle;\n        state K {\n            state K1;\n            [*] -> K1 : if [ready == 1];\n        }\n        [*] -> Idle;\n        [H] -> Idle;\n        [H*] -> K;\n        Idle -> K :: Go;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    Off -> O.[H] :: Resume;\n    Off -> O.[H*] :: ResumeDeep;\n    !O -> Off :: Stop;\n    Off -> Off :: Block effect { ready = 0; }\n}\n",
        "owners": [
            {
                "owner_path": [
                    "R",
                    "O"
                ],
                "record_variable": "__hist_O",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "shallow": [
                        "Idle"
                    ],
                    "deep": [
                        "K"
                    ]
                },
                "leaf_ids": {
                    "Idle": 4,
                    "K.K1": 6
                }
            }
        ],
        "initial_targets": {
            "R": [
                {
                    "target": "R.Off",
                    "guard": null,
                    "event": null,
                    "is_unconditional": true
                }
            ],
            "R.O": [
                {
                    "target": "R.O.K",
                    "guard": "__hist_goto >= 5 && __hist_goto <= 6",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.O.Idle",
                    "guard": "__hist_goto == 0 || __hist_goto == 4",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "merged"
                }
            ],
            "R.O.K": [
                {
                    "target": "R.O.K.K1",
                    "guard": "(__hist_goto == 0 || __hist_goto == 5) && ready == 1 || __hist_goto == 6",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "merged"
                }
            ]
        },
        "unconditional_missing": [
            {
                "composite_path": "R.O.K",
                "existing_conditional_count": 1,
                "first_child_name": "K1"
            }
        ]
    },
    "evented": {
        "source": "state R {\n    state Off;\n    state O {\n        event Kick;\n        state A;\n        state B;\n        [*] -> A :: Kick;\n        [H] -> B;\n        A -> B :: Next;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    Off -> O.[H] :: Resume;\n    !O -> Off :: Stop;\n}\n",
        "owners": [
            {
                "owner_path": [
                    "R",
                    "O"
                ],
                "record_variable": "__hist_O",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "shallow": [
                        "B"
                    ]
                },
                "leaf_ids": {
                    "A": 4,
                    "B": 5
                }
            }
        ],
        "initial_targets": {
            "R": [
                {
                    "target": "R.Off",
                    "guard": null,
                    "event": null,
                    "is_unconditional": true
                }
            ],
            "R.O": [
                {
                    "target": "R.O.B",
                    "guard": "__hist_goto == 5",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.O.A",
                    "guard": "__hist_goto == 4",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.O.__hist_gate_1",
                    "guard": "__hist_goto == 0",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "gate"
                }
            ]
        },
        "unconditional_missing": [
            {
                "composite_path": "R.O",
                "existing_conditional_count": 1,
                "first_child_name": "A"
            }
        ]
    },
    "nested": {
        "source": "state R {\n    state Off;\n    state O {\n        state S1;\n        state S2 {\n            state A2;\n            state B2;\n            [*] -> A2;\n            [H*] -> A2;\n            A2 -> B2 :: Next;\n        }\n        [*] -> S2.[H*];\n        [H] -> S1;\n    }\n    [*] -> Off;\n    Off -> O :: Fresh;\n    Off -> O.[H] :: Resume;\n    !O -> Off :: Stop;\n}\n",
        "owners": [
            {
                "owner_path": [
                    "R",
                    "O"
                ],
                "record_variable": "__hist_O",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "shallow": [
                        "S1"
                    ]
                },
                "leaf_ids": {
                    "S1": 4,
                    "S2.A2": 6,
                    "S2.B2": 7
                }
            },
            {
                "owner_path": [
                    "R",
                    "O",
                    "S2"
                ],
                "record_variable": "__hist_O_S2",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "deep": [
                        "A2"
                    ]
                },
                "leaf_ids": {
                    "A2": 6,
                    "B2": 7
                }
            }
        ],
        "initial_targets": {
            "R": [
                {
                    "target": "R.Off",
                    "guard": null,
                    "event": null,
                    "is_unconditional": true
                }
            ],
            "R.O": [
                {
                    "target": "R.O.S1",
                    "guard": "__hist_goto == 4",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.O.S2",
                    "guard": "__hist_goto >= 5 && __hist_goto <= 7",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.O.S2",
                    "guard": "__hist_goto == 0",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "gated"
                }
            ],
            "R.O.S2": [
                {
                    "target": "R.O.S2.B2",
                    "guard": "__hist_goto == 7",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.O.S2.A2",
                    "guard": "__hist_goto == 0 || __hist_goto == 5 || __hist_goto == 6",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "merged"
                }
            ]
        },
        "unconditional_missing": []
    },
    "siblings": {
        "source": "def int n = 0;\nstate R {\n    state Off;\n    state P {\n        state P1;\n        state P2;\n        [*] -> P1;\n        [H*] -> P1;\n        P1 -> P2 :: Next;\n    }\n    state Q {\n        state Q1;\n        state Q2 { state Q21; state Q22; [*] -> Q21; Q21 -> Q22 :: Next; }\n        [*] -> Q1;\n        [H*] -> Q1;\n        Q1 -> Q2 :: Next;\n    }\n    [*] -> Off;\n    Off -> P :: FreshP;\n    Off -> Q :: FreshQ;\n    Off -> P.[H*] :: ResumeP;\n    Off -> Q.[H*] :: ResumeQ;\n    !P -> Off :: Stop;\n    !Q -> Off :: Stop;\n}\n",
        "owners": [
            {
                "owner_path": [
                    "R",
                    "P"
                ],
                "record_variable": "__hist_P",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "deep": [
                        "P1"
                    ]
                },
                "leaf_ids": {
                    "P1": 4,
                    "P2": 5
                }
            },
            {
                "owner_path": [
                    "R",
                    "Q"
                ],
                "record_variable": "__hist_Q",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "deep": [
                        "Q1"
                    ]
                },
                "leaf_ids": {
                    "Q1": 7,
                    "Q2.Q21": 9,
                    "Q2.Q22": 10
                }
            }
        ],
        "initial_targets": {
            "R": [
                {
                    "target": "R.Off",
                    "guard": null,
                    "event": null,
                    "is_unconditional": true
                }
            ],
            "R.P": [
                {
                    "target": "R.P.P2",
                    "guard": "__hist_goto == 5",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.P.P1",
                    "guard": "__hist_goto == 0 || __hist_goto == 4",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "merged"
                }
            ],
            "R.Q": [
                {
                    "target": "R.Q.Q2",
                    "guard": "__hist_goto >= 8 && __hist_goto <= 10",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.Q.Q1",
                    "guard": "__hist_goto == 0 || __hist_goto == 7",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "merged"
                }
            ],
            "R.Q.Q2": [
                {
                    "target": "R.Q.Q2.Q22",
                    "guard": "__hist_goto == 10",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.Q.Q2.Q21",
                    "guard": "__hist_goto == 0 || __hist_goto == 9",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "merged"
                }
            ]
        },
        "unconditional_missing": []
    },
    "combo": {
        "source": "def int online = 0;\nstate R {\n    state Off;\n    state S {\n        state A;\n        state B;\n        [*] -> A;\n        [H*] -> A;\n        A -> B :: Next;\n    }\n    [*] -> Off;\n    Off -> S :: Fresh;\n    Off -> S.[H*] :: Resume + [online > 0];\n    Off -> Off :: Online effect { online = 1; }\n    !* -> Off :: Halt;\n}\n",
        "owners": [
            {
                "owner_path": [
                    "R",
                    "S"
                ],
                "record_variable": "__hist_S",
                "goto_variable": "__hist_goto",
                "defaults": {
                    "deep": [
                        "A"
                    ]
                },
                "leaf_ids": {
                    "A": 4,
                    "B": 5
                }
            }
        ],
        "initial_targets": {
            "R": [
                {
                    "target": "R.Off",
                    "guard": null,
                    "event": null,
                    "is_unconditional": true
                }
            ],
            "R.S": [
                {
                    "target": "R.S.B",
                    "guard": "__hist_goto == 5",
                    "event": null,
                    "is_unconditional": false,
                    "history_role": "route"
                },
                {
                    "target": "R.S.A",
                    "guard": "__hist_goto == 0 || __hist_goto == 4",
                    "event": null,
                    "is_unconditional": true,
                    "history_role": "merged"
                }
            ]
        },
        "unconditional_missing": []
    }
};
