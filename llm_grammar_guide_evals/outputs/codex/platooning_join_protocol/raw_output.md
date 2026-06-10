def int intended_position = 0;
def int platoon_normal = 1;
def int platoon_length = 0;
def int max_length = 8;
def int gap_created = 0;
def int agreement_received = 0;
def int lane_confirmed = 0;
def int close_enough = 0;
def int request_sent = 0;
def int increase_spacing_commanded = 0;
def int decrease_spacing_commanded = 0;
def int speed_control_enabled = 0;
def int steering_enabled = 0;
def int acknowledgement_sent = 0;
def int join_complete = 0;

state PlatooningJoinProtocol {
    [*] -> WaitingForJoin;

    state WaitingForJoin {
        enter {
            request_sent = 0;
            agreement_received = 0;
            gap_created = 0;
            lane_confirmed = 0;
            close_enough = 0;
            increase_spacing_commanded = 0;
            decrease_spacing_commanded = 0;
            speed_control_enabled = 0;
            steering_enabled = 0;
            acknowledgement_sent = 0;
            join_complete = 0;
        }
    }

    state RequestLeader {
        enter {
            request_sent = 1;
        }
    }

    state RearAgreement {
        enter {
            agreement_received = 1;
        }
    }

    state MiddleGapPreparation {
        enter {
            increase_spacing_commanded = 1;
        }
    }

    state MiddleAgreement {
        enter {
            agreement_received = 1;
        }
    }

    state LaneChanging;
    state SpeedControl {
        enter {
            speed_control_enabled = 1;
        }
    }

    state ApproachingPredecessor;
    state SteeringControl {
        enter {
            steering_enabled = 1;
        }
    }

    state Acknowledging {
        enter {
            acknowledgement_sent = 1;
        }
    }

    state RestoringGap {
        enter {
            decrease_spacing_commanded = 1;
        }
    }

    state Joined {
        enter {
            join_complete = 1;
        }
    }

    WaitingForJoin -> RequestLeader :: JoinRequested;
    RequestLeader -> RearAgreement : if [intended_position == 0 && platoon_normal > 0 && platoon_length < max_length];
    RequestLeader -> MiddleGapPreparation : if [intended_position != 0 && platoon_normal > 0];
    MiddleGapPreparation -> MiddleAgreement : if [gap_created > 0];
    RearAgreement -> LaneChanging : if [agreement_received > 0];
    MiddleAgreement -> LaneChanging : if [agreement_received > 0];
    LaneChanging -> SpeedControl : if [lane_confirmed > 0];
    SpeedControl -> ApproachingPredecessor : if [speed_control_enabled > 0];
    ApproachingPredecessor -> SteeringControl : if [lane_confirmed > 0 && close_enough > 0];
    SteeringControl -> Acknowledging : if [steering_enabled > 0];
    Acknowledging -> RestoringGap : if [acknowledgement_sent > 0];
    RestoringGap -> Joined : if [decrease_spacing_commanded > 0];
}
