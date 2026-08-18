"""TBE faculty API namespace.

* ``dashboard`` — the faculty home added in Step 7_24: the classrooms
  this person authors, each with its weekly-reflection completion,
  upcoming availability, and open-challenge count.
* ``classroom_signals`` — those two computations, shared with the
  classroom block of the unified group dashboard so both agree.
* ``availability`` — classroom-scoped Madrich availability (Step 4_7).
* ``challenges`` — the faculty side of the Challenge Log (Step 4_8).

Route discovery in ``api/urls.py`` is the only entry point.
"""
