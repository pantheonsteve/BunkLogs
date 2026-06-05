"""Shared name search helpers for Person querysets."""

from __future__ import annotations

from django.db.models import Q


def filter_persons_by_name_query(qs, q: str):
    """Match name tokens against first, last, and preferred name fields."""
    q = q.strip()
    if not q:
        return qs
    tokens = [t for t in q.split() if t]
    if not tokens:
        return qs
    if len(tokens) == 1:
        token = tokens[0]
        return qs.filter(
            Q(first_name__icontains=token)
            | Q(last_name__icontains=token)
            | Q(preferred_name__icontains=token),
        )
    combined = Q()
    for token in tokens:
        combined &= (
            Q(first_name__icontains=token)
            | Q(last_name__icontains=token)
            | Q(preferred_name__icontains=token)
        )
    return qs.filter(combined)
