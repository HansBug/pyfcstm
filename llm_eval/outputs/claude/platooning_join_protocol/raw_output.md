def int join_request_sent = 0;
def int intended_middle = 0;
def int platoon_normal = 1;
def int platoon_not_full = 1;
def int gap_created = 0;
def int agreement_received = 0;
def int in_correct_lane = 0;
def int close_enough = 0;
def int ack_sent = 0;
def int spacing_restored = 0;

state PlatoonJoinController {
    [*] -> Idle;

    state Idle;

    state Requesting {
        enter { join_request_sent = 1; }
    }

    state LeaderEvaluating {
        [*] -> Dispatch;

        state Dispatch;
        state RearCheck;
        state MiddleSpacing;
        state GrantAgreement {
            enter { agreement_received = 1; }
        }

        Dispatch -> RearCheck : if [intended_middle == 0];
        Dispatch -> MiddleSpacing : if [intended_middle > 0];
        RearCheck -> GrantAgreement : if [platoon_normal > 0 && platoon_not_full > 0];
        MiddleSpacing -> GrantAgreement : if [gap_created > 0];
    }

    state LaneChanging;

    state SpeedControlActive;

    state Approaching;

    state SteeringActive;

    state Acknowledging {
        enter { ack_sent = 1; }
    }

    state SpacingRestoring;

    state Joined {
        enter { spacing_restored = 1; }
    }

    Idle -> Requesting :: JoinRequested;
    Requesting -> LeaderEvaluating : if [join_request_sent > 0];
    LeaderEvaluating -> LaneChanging : if [agreement_received > 0];
    LaneChanging -> SpeedControlActive : if [in_correct_lane > 0];
    SpeedControlActive -> Approaching;
    Approaching -> SteeringActive : if [in_correct_lane > 0 && close_enough > 0];
    SteeringActive -> Acknowledging;
    Acknowledging -> SpacingRestoring : if [ack_sent > 0];
    SpacingRestoring -> Joined :: SpacingDecreased;
}
