"""Entry-thread and cohort-feed API namespace — Step 4_9.

* ``common`` — viewer resolution, the permission gates from §7, and the
  payload builders every role's homepage reuses.
* ``views`` — the shared ``/threads/`` endpoints.
* ``cohort`` — the cohort feed, reactions, and member list.

Every gate lives in ``common`` so faculty and director scoping has one
place to be wrong rather than five. Route discovery is ``api/urls.py``.
"""
