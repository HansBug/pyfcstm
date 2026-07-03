Parse and inspect pass cleanly — 0 errors, 0 warnings, 1 retained info (the intentional fall-through).

```
state Root {
    [*] -> Waiting;

    state Waiting;
    state Accepted;

    Waiting -> Accepted :: Request;
    Accepted -> [*];
}
```