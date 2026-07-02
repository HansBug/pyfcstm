state Root {
    [*] -> Waiting;

    state Waiting;
    state Recovering;
    state Done;

    Waiting -> Recovering :: Retry;
    Recovering -> Done :: Recovered;
    Done -> [*];
}