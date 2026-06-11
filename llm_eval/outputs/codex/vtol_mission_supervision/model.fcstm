def int data_link_ok = 1;
def int fly_home_request = 0;
def int search_track_request = 0;
def int payload_direct_command = 0;
def int operator_direct_command = 0;
def int mission_active = 0;
def int command_active = 0;
def int off_count = 0;
def int standby_count = 0;
def int slow_down_count = 0;

state VTOLMissionSupervisor {
    [*] -> StandBy;

    !* -> MissionControllerOff :: PowerOff;
    !* -> StandBy :: StandByRequested;
    !* -> SlowDown :: SlowDownRequested;

    state MissionControllerOff {
        enter { off_count = off_count + 1; }
    }

    state StandBy {
        enter {
            standby_count = standby_count + 1;
            mission_active = 0;
            command_active = 0;
        }
    }

    state SlowDown {
        enter { slow_down_count = slow_down_count + 1; }
    }

    state MissionMode {
        [*] -> ParseCommand;

        enter {
            mission_active = 1;
            command_active = 0;
        }

        state ParseCommand;
        state FlyHome {
            enter { fly_home_request = 0; }
        }
        state SearchAndTrackObject {
            enter { search_track_request = 0; }
        }
        state ExecuteMissionLeg;
        state HoldPosition;

        ParseCommand -> FlyHome : if [fly_home_request > 0 || data_link_ok == 0];
        ParseCommand -> SearchAndTrackObject : if [search_track_request > 0 && data_link_ok > 0];
        ParseCommand -> ExecuteMissionLeg : if [fly_home_request == 0 && search_track_request == 0 && data_link_ok > 0];
        FlyHome -> ParseCommand :: FlyHomeComplete;
        SearchAndTrackObject -> ParseCommand :: SearchTrackComplete;
        ExecuteMissionLeg -> ParseCommand :: MissionLegComplete;
        ExecuteMissionLeg -> HoldPosition : if [data_link_ok == 0];
        HoldPosition -> ParseCommand : if [data_link_ok > 0];
    }

    state CommandMode {
        [*] -> DirectCommand;

        enter {
            command_active = 1;
            mission_active = 0;
        }

        state DirectCommand;
        state PayloadOverride;
        state OperatorOverride;

        DirectCommand -> PayloadOverride : if [payload_direct_command > 0];
        DirectCommand -> OperatorOverride : if [operator_direct_command > 0];
        PayloadOverride -> DirectCommand :: PayloadCommandComplete;
        OperatorOverride -> DirectCommand :: OperatorCommandComplete;
    }

    StandBy -> MissionMode :: StartMission;
    StandBy -> CommandMode :: DirectCommandRequested;
    MissionMode -> CommandMode : if [payload_direct_command > 0 || operator_direct_command > 0];
    CommandMode -> MissionMode :: ResumeMission;
}
