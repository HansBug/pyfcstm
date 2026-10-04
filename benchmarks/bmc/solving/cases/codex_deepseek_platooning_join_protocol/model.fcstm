def int request_sent = 0;
def int agreement_received = 0;
def int lane_changed = 0;
def int speed_control_on = 0;
def int close_enough = 0;
def int steering_on = 0;
def int ack_sent = 0;

state PlatoonJoin {
    [*] -> Cruising;

    state Cruising;

    state Requesting {
        enter { request_sent = 1; }
    }

    state Aligning {
        enter { lane_changed = 1; speed_control_on = 1; }
    }

    state Approaching;

    state Merging {
        enter { steering_on = 1; }
    }

    state Acknowledged {
        enter { ack_sent = 1; }
    }

    Cruising -> Requesting :: JoinRequested;
    Requesting -> Aligning : if [agreement_received > 0];
    Aligning -> Approaching : if [lane_changed > 0];
    Approaching -> Merging : if [close_enough > 0 && speed_control_on > 0];
    Merging -> Acknowledged :: AckSent;
}
