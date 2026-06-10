def int current_floor = 0;
def int floor_request = 0;
def int car_destination = 0;
def int rank_ok = 0;
def int request_active = 0;
def int destination_active = 0;
def int service_done = 0;
def int sync_ready = 0;

state LiftObject {
    [*] -> Sync;

    state Sync {
        during { sync_ready = 1; }
    }

    state Stop {
        enter { service_done = 0; }
    }

    state Serving {
        enter {
            service_done = 1;
            floor_request = 0;
            car_destination = 0;
            request_active = 0;
            destination_active = 0;
        }
    }

    state Up {
        during { current_floor = current_floor + 1; }
    }

    state Down {
        during { current_floor = current_floor - 1; }
    }

    Sync -> Stop : if [sync_ready > 0];

    Stop -> Serving : if [destination_active > 0 && car_destination == current_floor];
    Stop -> Serving : if [request_active > 0 && rank_ok > 0 && floor_request == current_floor];

    Stop -> Up : if [destination_active > 0 && car_destination > current_floor];
    Stop -> Up : if [request_active > 0 && rank_ok > 0 && floor_request > current_floor];

    Stop -> Down : if [destination_active > 0 && car_destination < current_floor];
    Stop -> Down : if [request_active > 0 && rank_ok > 0 && floor_request < current_floor];

    Up -> Stop : if [destination_active > 0 && car_destination == current_floor];
    Up -> Stop : if [request_active > 0 && rank_ok > 0 && floor_request == current_floor];

    Down -> Stop : if [destination_active > 0 && car_destination == current_floor];
    Down -> Stop : if [request_active > 0 && rank_ok > 0 && floor_request == current_floor];

    Serving -> Sync : if [service_done > 0];
}
