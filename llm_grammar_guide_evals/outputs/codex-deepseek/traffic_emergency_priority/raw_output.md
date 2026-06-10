def int ambulance_north = 0;
def int ambulance_south = 0;
def int ambulance_east = 0;
def int ambulance_west = 0;
def int cars_north = 0;
def int cars_south = 0;
def int cars_east = 0;
def int cars_west = 0;
def int neighbor_command = 0;

state TrafficController {
    [*] -> NormalOperation;

    state NormalOperation {
        [*] -> Acquiring;

        state Acquiring;
        state NorthGreen;
        state SouthGreen;
        state EastGreen;
        state WestGreen;
        state EmergencyGreen;

        Acquiring -> EmergencyGreen : if [ambulance_north > 0 || ambulance_south > 0 || ambulance_east > 0 || ambulance_west > 0] effect {
            neighbor_command = 1;
        };

        Acquiring -> NorthGreen : if [ambulance_north == 0 && ambulance_south == 0 && ambulance_east == 0 && ambulance_west == 0 && cars_north > 10 && cars_south == 0 && cars_east == 0 && cars_west == 0];

        Acquiring -> SouthGreen : if [ambulance_north == 0 && ambulance_south == 0 && ambulance_east == 0 && ambulance_west == 0 && cars_south > 10 && cars_north == 0 && cars_east == 0 && cars_west == 0];

        Acquiring -> EastGreen : if [ambulance_north == 0 && ambulance_south == 0 && ambulance_east == 0 && ambulance_west == 0 && cars_east > 10 && cars_north == 0 && cars_south == 0 && cars_west == 0];

        Acquiring -> WestGreen : if [ambulance_north == 0 && ambulance_south == 0 && ambulance_east == 0 && ambulance_west == 0 && cars_west > 10 && cars_north == 0 && cars_south == 0 && cars_east == 0];

        NorthGreen -> Acquiring :: CycleComplete;
        SouthGreen -> Acquiring :: CycleComplete;
        EastGreen -> Acquiring :: CycleComplete;
        WestGreen -> Acquiring :: CycleComplete;

        EmergencyGreen -> Acquiring : if [ambulance_north == 0 && ambulance_south == 0 && ambulance_east == 0 && ambulance_west == 0];
    }
}
