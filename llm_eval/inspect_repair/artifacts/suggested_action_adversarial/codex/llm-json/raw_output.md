state Root {
    [*] -> Service;

    state Service;
    state Fault;
    state Shutdown;

    Service -> Fault :: Disabled;
    Fault -> Shutdown;
    Shutdown -> [*];
}