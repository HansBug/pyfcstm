def int ambulance_north = 0;
def int ambulance_east = 0;
def int ambulance_south = 0;
def int ambulance_west = 0;
def int cars_north = 0;
def int cars_east = 0;
def int cars_south = 0;
def int cars_west = 0;
def int neighbor_green_cmd = 0;
def int image_ready = 0;

state TrafficController {
    [*] -> Acquiring;

    state Acquiring {
        during { image_ready = 1; }
    }

    state Normal {
        [*] -> NorthGreen;

        state NorthGreen;
        state EastGreen;
        state SouthGreen;
        state WestGreen;

        NorthGreen -> EastGreen : if [cars_east > 10 && cars_north == 0 && cars_south == 0 && cars_west == 0];
        NorthGreen -> SouthGreen : if [cars_south > 10 && cars_north == 0 && cars_east == 0 && cars_west == 0];
        NorthGreen -> WestGreen : if [cars_west > 10 && cars_north == 0 && cars_east == 0 && cars_south == 0];
        EastGreen -> NorthGreen : if [cars_north > 10 && cars_east == 0 && cars_south == 0 && cars_west == 0];
        EastGreen -> SouthGreen : if [cars_south > 10 && cars_north == 0 && cars_east == 0 && cars_west == 0];
        EastGreen -> WestGreen : if [cars_west > 10 && cars_north == 0 && cars_east == 0 && cars_south == 0];
        SouthGreen -> NorthGreen : if [cars_north > 10 && cars_east == 0 && cars_south == 0 && cars_west == 0];
        SouthGreen -> EastGreen : if [cars_east > 10 && cars_north == 0 && cars_south == 0 && cars_west == 0];
        SouthGreen -> WestGreen : if [cars_west > 10 && cars_north == 0 && cars_east == 0 && cars_south == 0];
        WestGreen -> NorthGreen : if [cars_north > 10 && cars_east == 0 && cars_south == 0 && cars_west == 0];
        WestGreen -> EastGreen : if [cars_east > 10 && cars_north == 0 && cars_south == 0 && cars_west == 0];
        WestGreen -> SouthGreen : if [cars_south > 10 && cars_north == 0 && cars_east == 0 && cars_west == 0];
    }

    state Emergency {
        [*] -> EmergencyNorth;

        state EmergencyNorth {
            enter { neighbor_green_cmd = 1; }
        }
        state EmergencyEast {
            enter { neighbor_green_cmd = 1; }
        }
        state EmergencySouth {
            enter { neighbor_green_cmd = 1; }
        }
        state EmergencyWest {
            enter { neighbor_green_cmd = 1; }
        }

        EmergencyNorth -> EmergencyEast : if [ambulance_east > 0 && ambulance_north == 0];
        EmergencyNorth -> EmergencySouth : if [ambulance_south > 0 && ambulance_north == 0 && ambulance_east == 0];
        EmergencyNorth -> EmergencyWest : if [ambulance_west > 0 && ambulance_north == 0 && ambulance_east == 0 && ambulance_south == 0];
        EmergencyEast -> EmergencyNorth : if [ambulance_north > 0 && ambulance_east == 0];
        EmergencyEast -> EmergencySouth : if [ambulance_south > 0 && ambulance_north == 0 && ambulance_east == 0];
        EmergencyEast -> EmergencyWest : if [ambulance_west > 0 && ambulance_north == 0 && ambulance_east == 0 && ambulance_south == 0];
        EmergencySouth -> EmergencyNorth : if [ambulance_north > 0 && ambulance_south == 0];
        EmergencySouth -> EmergencyEast : if [ambulance_east > 0 && ambulance_north == 0 && ambulance_south == 0];
        EmergencySouth -> EmergencyWest : if [ambulance_west > 0 && ambulance_north == 0 && ambulance_east == 0 && ambulance_south == 0];
        EmergencyWest -> EmergencyNorth : if [ambulance_north > 0 && ambulance_west == 0];
        EmergencyWest -> EmergencyEast : if [ambulance_east > 0 && ambulance_north == 0 && ambulance_west == 0];
        EmergencyWest -> EmergencySouth : if [ambulance_south > 0 && ambulance_north == 0 && ambulance_east == 0 && ambulance_west == 0];
    }

    Acquiring -> Emergency : if [ambulance_north > 0 || ambulance_east > 0 || ambulance_south > 0 || ambulance_west > 0];
    Acquiring -> Normal : if [image_ready > 0 && ambulance_north == 0 && ambulance_east == 0 && ambulance_south == 0 && ambulance_west == 0];
    Normal -> Emergency : if [ambulance_north > 0 || ambulance_east > 0 || ambulance_south > 0 || ambulance_west > 0];
    Normal -> Acquiring : if [cars_north == 0 && cars_east == 0 && cars_south == 0 && cars_west == 0];
    Emergency -> Acquiring : if [ambulance_north == 0 && ambulance_east == 0 && ambulance_south == 0 && ambulance_west == 0];
}
