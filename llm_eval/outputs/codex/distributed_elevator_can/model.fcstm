def int current_floor = 0;
def int floor_request = -1;
def int car_destination = -1;
def int rank_decision = 0;
def int hall_request_pending = 0;
def int car_request_pending = 0;
def int target_floor = 0;
def int service_floor = -1;
def int door_open = 0;
def int state_broadcast_pending = 0;
def int process_data_synced = 0;

state DistributedElevatorCan {
    [*] -> STOP;

    state STOP {
        enter {
            state_broadcast_pending = 1;
            door_open = 0;
        }

        during {
            process_data_synced = 1;
        }
    }

    state UP {
        during {
            current_floor = current_floor + 1;
            state_broadcast_pending = 1;
        }
    }

    state DOWN {
        during {
            current_floor = current_floor - 1;
            state_broadcast_pending = 1;
        }
    }

    STOP -> STOP : if [floor_request == current_floor && hall_request_pending > 0 && rank_decision > 0] effect {
        service_floor = current_floor;
        floor_request = -1;
        hall_request_pending = 0;
        door_open = 1;
        state_broadcast_pending = 1;
    }

    STOP -> STOP : if [car_destination == current_floor && car_request_pending > 0] effect {
        service_floor = current_floor;
        car_destination = -1;
        car_request_pending = 0;
        door_open = 1;
        state_broadcast_pending = 1;
    }

    STOP -> UP : if [hall_request_pending > 0 && rank_decision > 0 && floor_request > current_floor] effect {
        target_floor = floor_request;
        door_open = 0;
    }

    STOP -> DOWN : if [hall_request_pending > 0 && rank_decision > 0 && floor_request < current_floor] effect {
        target_floor = floor_request;
        door_open = 0;
    }

    STOP -> UP : if [car_request_pending > 0 && car_destination > current_floor] effect {
        target_floor = car_destination;
        door_open = 0;
    }

    STOP -> DOWN : if [car_request_pending > 0 && car_destination < current_floor] effect {
        target_floor = car_destination;
        door_open = 0;
    }

    UP -> STOP : if [current_floor >= target_floor];

    DOWN -> STOP : if [current_floor <= target_floor];

    STOP -> STOP :: HallRequestReceived;

    STOP -> STOP :: CarDestinationSelected;

    STOP -> STOP : /StateBroadcastTick;
}
