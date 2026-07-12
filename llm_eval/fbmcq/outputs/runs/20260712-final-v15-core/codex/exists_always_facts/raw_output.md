init state("Root.Idle");
assume event("Root.Go", 0) == true;
check exists_always <= 1: x == 0;
