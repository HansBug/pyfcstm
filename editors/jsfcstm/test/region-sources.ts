/**
 * FCSTM sources whose diagrams exercise region layout: several regions in one
 * owner, an owner nested inside a region, edges that enter and leave the owner
 * and regions of very different heights. Kept as literals so the jsfcstm tests
 * do not depend on any file outside this tree.
 */

export const CONTROLLER_SOURCE = `input int fault;
input int requested;
control int permit = 0;
output int motor = 0;

state Controller {
    event Start;
    event Stop;
    [*] -> Idle;
    state Idle { during { motor = 0; } }

    state Running {
        enter { permit = 0; }
        region Safety {
            >> during before { permit = 1; }
            [*] -> Normal;
            state Normal {
                during {
                    if [fault != 0] { permit = 0; }
                }
            }
            state Tripped;
            Normal -> Tripped : if [fault != 0];
        }
        region Motion {
            event Kick;
            [*] -> Off;
            state Off { during { motor = 0; } }
            state On {
                during {
                    if [active("Controller.Running.Safety.Tripped")] { motor = 0; }
                    else { motor = 1; }
                }
            }
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [active("/Running.Safety.Tripped")];
            On -> Off : Kick;
        }
    }

    Idle -> Running : /Start;
    !Running -> Idle : /Stop;
}
`;

export const NESTED_SOURCE = `input int proceed;

state Workflow {
    event A1Done;
    event A2Done;
    event ADone;
    event BDone;
    event CDone;
    event Cancel;
    [*] -> Job;
    state Job {
        region A {
            [*] -> Q;
            state Q {
                region A1 {
                    [*] -> Working;
                    state Working;
                    Working -> [*] : /A1Done;
                }
                region A2 {
                    [*] -> Working;
                    state Working;
                    Working -> [*] : /A2Done;
                }
            }
            state Packing;
            Q -> Packing;
            Packing -> [*] : /ADone;
        }
        region B {
            [*] -> Working;
            state Working;
            Working -> [*] : /BDone;
        }
        region C {
            [*] -> Working;
            state Working;
            Working -> [*] : /CDone;
        }
    }
    state AwaitPermission;
    state Ready;
    state Idle;
    Job -> AwaitPermission;
    AwaitPermission -> Ready : if [proceed != 0];
    !Job -> Idle : /Cancel;
}
`;

export const ELEVATOR_SOURCE = `input int call_floor;
input int overload;
control int door_blocked = 0;
output int motor_cmd = 0;
output int door_cmd = 0;
output int alarm = 0;

state Elevator {
    event Dispatch;
    event Reset;
    [*] -> Idle;
    state Idle { during { motor_cmd = 0; door_cmd = 0; } }

    state Serving {
        region Door {
            [*] -> Closed;
            state Closed { during { door_cmd = 0; } }
            state Opening { during { door_cmd = 1; } }
            state Open { during { door_cmd = 1; } }
            Closed -> Opening : if [active("Elevator.Serving.Motion.Stopped") && call_floor != 0];
            Opening -> Open;
            Open -> Closed : if [door_blocked == 0 && overload == 0];
        }
        region Motion {
            >> during after { if [overload != 0] { motor_cmd = 0; } }
            [*] -> Stopped;
            state Stopped { during { motor_cmd = 0; } }
            state Moving { during { motor_cmd = 1; } }
            Stopped -> Moving : if [active("Elevator.Serving.Door.Closed") && call_floor != 0];
            Moving -> Stopped : if [call_floor == 0] effect { motor_cmd = 0; }
        }
        region Alarm {
            [*] -> Quiet;
            state Quiet { during { alarm = 0; } }
            state Ringing { during { alarm = 1; } }
            Quiet -> Ringing : if [overload != 0 || door_blocked != 0];
            Ringing -> Quiet : if [overload == 0 && door_blocked == 0];
        }
    }

    Idle -> Serving : /Dispatch;
    !Serving -> Idle : /Reset;
}
`;

export const JOB_SOURCE = `input int proceed;

state Workflow {
    event ADone;
    event BDone;
    event Cancel;
    [*] -> Job;
    state Job {
        region A {
            [*] -> Working;
            state Working;
            Working -> [*] : /ADone;
        }
        region B {
            [*] -> Working;
            state Working;
            Working -> [*] : /BDone;
        }
    }
    state AwaitPermission;
    state Ready;
    state Idle;
    Job -> AwaitPermission;
    AwaitPermission -> Ready : if [proceed != 0];
    !Job -> Idle : /Cancel;
}
`;

export const WIDE_SOURCE = `input int a;
state Plant {
    [*] -> Run;
    state Run {
        region R1 { [*] -> S1; state S1; state S2; S1 -> S2 : if [a > 1]; S2 -> S1 : if [a < 1]; }
        region R2 { [*] -> T1; state T1; }
        region R3 { [*] -> U1; state U1; state U2; state U3; U1 -> U2 : if [a > 2]; U2 -> U3 : if [a > 3]; U3 -> U1 : if [a > 4]; }
        region R4 { [*] -> V1; state V1; state V2; V1 -> V2 : if [a > 5]; }
        region R5 { [*] -> W1; state W1; }
        region R6 { [*] -> X1; state X1; state X2; state X3; state X4; X1 -> X2 : if [a>1]; X2 -> X3 : if [a>2]; X3 -> X4 : if [a>3]; }
    }
    state Off;
    Off -> Run : if [a > 0];
    Run -> Off : if [a < 0];
}
`;


/** Region names far wider than the states they hold: the titles decide how wide a region is. */
export const LONG_TITLES_SOURCE = `def int x = 0;
state Root {
    [*] -> O;
    state O {
        region TemperatureMonitoringSupervisor { [*] -> A; state A; }
        region PressureSupervisionController { [*] -> C; state C; }
        region Logger { [*] -> L; state L; }
    }
}
`;

/** Every source above with a readable name. */
export const REGION_SOURCES: Array<[string, string]> = [
    ['controller', CONTROLLER_SOURCE],
    ['nested', NESTED_SOURCE],
    ['elevator', ELEVATOR_SOURCE],
    ['job', JOB_SOURCE],
    ['wide', WIDE_SOURCE],
    ['long-titles', LONG_TITLES_SOURCE],
];

/** A machine without regions: its drawing must stay what it was before regions existed. */
export const PLAIN_SOURCE = `input int x;
state Root {
    [*] -> A;
    state A;
    state B;
    A -> B : if [x > 0];
}
`;
