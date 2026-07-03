def int retry = 0;

state Root {
    [*] -> Waiting;

    state Waiting {
        during {
            retry = retry + 1;
        }
    }
    state Recovering;
    state Done;

    Waiting -> Recovering : if [retry > 0];
    Recovering -> Done;
    Done -> [*];
}