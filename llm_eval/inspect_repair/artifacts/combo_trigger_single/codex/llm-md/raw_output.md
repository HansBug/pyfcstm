state Root {
    [*] -> Waiting;

    state Waiting;
    state Accepted;

    Waiting -> Accepted :: Request;
    Accepted -> [*];
}