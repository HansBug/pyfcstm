Repair the following FBMCQ query after the parser reported that the property
body is missing its colon. Keep the stated verification intent unchanged.

The exact authorized facts are: `Root.Idle` and `Root.Done` are state paths;
`Root.Go` is a parent-scoped event path; hot-starting in `Root.Idle` and
requiring `Root.Go` at step 0 reaches `Root.Done` within one step. Do not add
another assumption, initialization rule, or model fact.

Broken query:

```fbmcq
init state("Root.Idle");
assume event("Root.Go", 0) == true;
check reach <= 1 active("Root.Done");
```

Parser diagnostic: expected `:` after `check reach <= 1`.
