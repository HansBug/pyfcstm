"""
End-to-end checks of the models with regions.

The module holds the names of the shared semantic fixtures that the end-to-end
checks and the native runtime checks both walk through.

The module contains:

* :data:`MODEL_CASES` - The ids of the five models of the closing checks.

Example::

    >>> from test.end_to_end import MODEL_CASES
    >>> len(MODEL_CASES)
    5
"""

#: A controller interlock, a job with a completing region, a nested group, a group
#: preemption and a collaboration through ``active()``.
MODEL_CASES = (
    "region_controller_interlock_prototype_trace",
    "region_done_region_waits_and_last_completion_continues_same_cycle",
    "region_group_exit_takes_a_nested_group_out_before_its_owner",
    "region_group_preemption_wins_over_child_completion_in_same_cycle",
    "region_active_query_follows_enter_exit_effect_and_same_cycle_order",
)
