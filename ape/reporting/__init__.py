"""Adaptive client reporting — the generation pipeline.

This package used to re-export the D1 selection module. There is no D1: a
template is either named by the advisor or composed by the model, and
neither is a bandit arm. The names that lived here (cell_key, eligible_arms,
score_arms, select, blend_prior, effective_profile) went with it. Nothing
imported them but the selector itself.

What survived the removal lives where it belongs:

    generate.py   builds a report from a template and a frozen snapshot
    composer.py   designs a one-off template from the block registry
    registry.py   the block palette both of those draw from
    d2.py         the ONLY remaining bandit — which answer format a chat
                  question gets, rewarded by the thumbs on that answer
    rewards.py    engagement accrual and the preference profile
    skill.py      the written brief the composer reads

Deliberately empty of re-exports. A package __init__ that forwards a
module's names makes the same function importable by two paths, and the
one that goes stale is the one nobody edits.
"""
