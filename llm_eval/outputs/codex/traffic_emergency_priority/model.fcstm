def int north_waiting = 0;
def int east_waiting = 0;
def int south_waiting = 0;
def int west_waiting = 0;
def int north_ambulance = 0;
def int east_ambulance = 0;
def int south_ambulance = 0;
def int west_ambulance = 0;
def int north_green = 0;
def int east_green = 0;
def int south_green = 0;
def int west_green = 0;
def int neighbor_green_command = 0;
def int acquisition_count = 0;

state TrafficEmergencyPriority {
    [*] -> AcquireImages;

    state AcquireImages {
        during {
            acquisition_count = acquisition_count + 1;
        }
    }

    state ClassifyTraffic;
    state OrdinaryTraffic;
    state NorthEmergencyGreen {
        enter {
            north_green = 1;
            east_green = 0;
            south_green = 0;
            west_green = 0;
            neighbor_green_command = 1;
        }
    }
    state EastEmergencyGreen {
        enter {
            north_green = 0;
            east_green = 1;
            south_green = 0;
            west_green = 0;
            neighbor_green_command = 1;
        }
    }
    state SouthEmergencyGreen {
        enter {
            north_green = 0;
            east_green = 0;
            south_green = 1;
            west_green = 0;
            neighbor_green_command = 1;
        }
    }
    state WestEmergencyGreen {
        enter {
            north_green = 0;
            east_green = 0;
            south_green = 0;
            west_green = 1;
            neighbor_green_command = 1;
        }
    }
    state NorthCrowdedGreen {
        enter {
            north_green = 1;
            east_green = 0;
            south_green = 0;
            west_green = 0;
            neighbor_green_command = 0;
        }
    }
    state EastCrowdedGreen {
        enter {
            north_green = 0;
            east_green = 1;
            south_green = 0;
            west_green = 0;
            neighbor_green_command = 0;
        }
    }
    state SouthCrowdedGreen {
        enter {
            north_green = 0;
            east_green = 0;
            south_green = 1;
            west_green = 0;
            neighbor_green_command = 0;
        }
    }
    state WestCrowdedGreen {
        enter {
            north_green = 0;
            east_green = 0;
            south_green = 0;
            west_green = 1;
            neighbor_green_command = 0;
        }
    }

    AcquireImages -> ClassifyTraffic;
    ClassifyTraffic -> NorthEmergencyGreen : if [north_ambulance > 0];
    ClassifyTraffic -> EastEmergencyGreen : if [north_ambulance == 0 && east_ambulance > 0];
    ClassifyTraffic -> SouthEmergencyGreen : if [north_ambulance == 0 && east_ambulance == 0 && south_ambulance > 0];
    ClassifyTraffic -> WestEmergencyGreen : if [north_ambulance == 0 && east_ambulance == 0 && south_ambulance == 0 && west_ambulance > 0];
    ClassifyTraffic -> NorthCrowdedGreen : if [north_ambulance == 0 && east_ambulance == 0 && south_ambulance == 0 && west_ambulance == 0 && north_waiting > 10 && east_waiting == 0 && south_waiting == 0 && west_waiting == 0];
    ClassifyTraffic -> EastCrowdedGreen : if [north_ambulance == 0 && east_ambulance == 0 && south_ambulance == 0 && west_ambulance == 0 && east_waiting > 10 && north_waiting == 0 && south_waiting == 0 && west_waiting == 0];
    ClassifyTraffic -> SouthCrowdedGreen : if [north_ambulance == 0 && east_ambulance == 0 && south_ambulance == 0 && west_ambulance == 0 && south_waiting > 10 && north_waiting == 0 && east_waiting == 0 && west_waiting == 0];
    ClassifyTraffic -> WestCrowdedGreen : if [north_ambulance == 0 && east_ambulance == 0 && south_ambulance == 0 && west_ambulance == 0 && west_waiting > 10 && north_waiting == 0 && east_waiting == 0 && south_waiting == 0];
    ClassifyTraffic -> OrdinaryTraffic : if [north_ambulance == 0 && east_ambulance == 0 && south_ambulance == 0 && west_ambulance == 0 && !(north_waiting > 10 && east_waiting == 0 && south_waiting == 0 && west_waiting == 0) && !(east_waiting > 10 && north_waiting == 0 && south_waiting == 0 && west_waiting == 0) && !(south_waiting > 10 && north_waiting == 0 && east_waiting == 0 && west_waiting == 0) && !(west_waiting > 10 && north_waiting == 0 && east_waiting == 0 && south_waiting == 0)];
    OrdinaryTraffic -> AcquireImages;
    NorthEmergencyGreen -> AcquireImages;
    EastEmergencyGreen -> AcquireImages;
    SouthEmergencyGreen -> AcquireImages;
    WestEmergencyGreen -> AcquireImages;
    NorthCrowdedGreen -> AcquireImages;
    EastCrowdedGreen -> AcquireImages;
    SouthCrowdedGreen -> AcquireImages;
    WestCrowdedGreen -> AcquireImages;
}
