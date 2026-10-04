def int link_ok = 1;
def int fly_home_request = 0;
def int search_track_request = 0;
def int direct_command_active = 0;
def int mission_command_ready = 0;
def int power_off_request = 0;
def int slow_down_request = 0;

state MissionSupervisor {
    [*] -> StandBy;

    state StandBy;
    state MissionControllerOff;
    state SlowDown;

    state MissionMode {
        [*] -> ParseCommand;

        state ParseCommand;
        state FlyHome;
        state SearchAndTrack;
        state ExecuteWaypoint;

        ParseCommand -> FlyHome : if [fly_home_request > 0];
        ParseCommand -> SearchAndTrack : if [search_track_request > 0 && fly_home_request == 0];
        ParseCommand -> ExecuteWaypoint : if [mission_command_ready > 0 && fly_home_request == 0 && search_track_request == 0];
        FlyHome -> ParseCommand :: FlyHomeComplete;
        SearchAndTrack -> ParseCommand :: SearchTrackComplete;
        ExecuteWaypoint -> ParseCommand :: WaypointComplete;
    }

    state CommandMode {
        [*] -> AwaitDirect;

        state AwaitDirect;
        state ExecuteDirect;

        AwaitDirect -> ExecuteDirect : if [direct_command_active > 0];
        ExecuteDirect -> AwaitDirect :: DirectComplete;
    }

    StandBy -> MissionMode :: MissionStart;
    MissionMode -> CommandMode : if [direct_command_active > 0];
    CommandMode -> MissionMode :: DirectReleased;
    MissionMode -> SlowDown : if [link_ok == 0 || slow_down_request > 0];
    CommandMode -> SlowDown : if [link_ok == 0 || slow_down_request > 0];
    SlowDown -> StandBy :: Recovered;
    MissionMode -> StandBy :: AbortMission;
    CommandMode -> StandBy :: AbortMission;
    StandBy -> MissionControllerOff : if [power_off_request > 0];
}
