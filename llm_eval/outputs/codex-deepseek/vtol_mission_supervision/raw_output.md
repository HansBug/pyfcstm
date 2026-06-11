def int fly_home_request = 0;
def int search_track_request = 0;
def int direct_command_request = 0;
def int link_ok = 1;
def int slow_down_request = 0;
def int mission_off_request = 0;

state VTOLMissionManager {
    [*] -> MissionMode;

    state MissionMode {
        [*] -> ParseCommand;

        state ParseCommand;
        state FlyHome;
        state SearchTrack;
        state TakeOff;
        state Loiter;
        state Land;

        ParseCommand -> TakeOff :: TakeOffCommand;
        TakeOff -> ParseCommand :: TakeOffComplete;
        ParseCommand -> Loiter :: LoiterCommand;
        Loiter -> ParseCommand :: LoiterComplete;
        ParseCommand -> FlyHome : if [fly_home_request > 0 && link_ok > 0];
        FlyHome -> ParseCommand :: FlyHomeComplete;
        ParseCommand -> SearchTrack : if [search_track_request > 0 && link_ok > 0];
        SearchTrack -> ParseCommand :: SearchTrackComplete;
        ParseCommand -> Land :: LandCommand;
        Land -> ParseCommand :: LandComplete;
    }

    state CommandMode {
        [*] -> ParseDirectCommand;

        state ParseDirectCommand;
        state OperatorDirect;
        state PayloadDirect;

        ParseDirectCommand -> OperatorDirect :: OperatorOverride;
        ParseDirectCommand -> PayloadDirect :: PayloadOverride;
        OperatorDirect -> ParseDirectCommand :: OperatorComplete;
        PayloadDirect -> ParseDirectCommand :: PayloadComplete;
    }

    state StandBy;
    state MissionControllerOff;
    state SlowDown;

    MissionMode -> CommandMode : if [direct_command_request > 0];
    CommandMode -> MissionMode :: ResumeMission;

    MissionMode -> StandBy :: AllStop;
    MissionMode -> MissionControllerOff : if [mission_off_request > 0];
    MissionMode -> SlowDown :: SlowDownCommand;
    CommandMode -> StandBy :: AllStop;
    CommandMode -> MissionControllerOff : if [mission_off_request > 0];
    CommandMode -> SlowDown :: SlowDownCommand;
}
