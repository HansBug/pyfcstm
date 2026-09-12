def int current_floor = 0;
def int floor_request = 0;
def int car_destination = 0;
def int rank_decision = 0;

state LiftObject {
    [*] -> STOP;

    state STOP {
        [*] -> Idle;

        state Idle;
        state Serving {
            enter {
                floor_request = 0;
                car_destination = 0;
            }
        }

        Idle -> Serving : if [floor_request == current_floor || car_destination == current_floor];
        Serving -> Idle :: ServiceComplete;
    }

    state UP {
        during { current_floor = current_floor + 1; }
    }
    state DOWN {
        during { current_floor = current_floor - 1; }
    }

    STOP -> UP : if [rank_decision > 0 && (floor_request > current_floor || car_destination > current_floor)];
    STOP -> DOWN : if [rank_decision > 0 && ((floor_request < current_floor && floor_request > 0) || (car_destination < current_floor && car_destination > 0))];
    UP -> STOP : if [floor_request == current_floor || car_destination == current_floor];
    DOWN -> STOP : if [floor_request == current_floor || car_destination == current_floor];
}
