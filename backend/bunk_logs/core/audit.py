"""Audit trail helpers (Step 7_4).

Single source of truth for "who did what when" event writes. Every call
site that mutates content / relationships / orders / supervisions / flags
should funnel through one of the helpers below so the event shape stays
consistent and the AuditEvent table is genuinely complete.

Canonical product spec: ``docs/user_stories/00_cross_cutting/audit_trail.md``.

Design notes for callers:

* Helpers accept an ``actor`` of either a ``Membership`` or a Django User;
  whichever they have at the call site, we coerce to both columns. Tests
  that pass a stub object with ``.user`` / ``.person`` attrs are tolerated.
* ``content`` is duck-typed: any model with ``.id`` / ``.organization`` /
  ``.program`` (or ``.organization_id`` / ``.program_id``) works. The
  caller controls ``content_type`` via the helper signature or the model's
  optional ``_audit_content_type_label()`` method.
* Snapshots are caller-provided dicts; the audit module does not introspect
  content rows so it stays agnostic to schema changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from bunk_logs.core.models import AuditEvent
from bunk_logs.core.models import Membership

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_actor(actor: Any) -> tuple[Membership | None, AbstractBaseUser | None]:
    """Return ``(actor_membership, actor_user)`` for any plausible input.

    Accepts a Membership, a User, or a duck-typed object with ``.membership``
    / ``.user`` attrs. Either column may be None when the call site only has
    one (e.g. Super Admin override has no Membership row).
    """
    if actor is None:
        return None, None
    if isinstance(actor, Membership):
        user = getattr(getattr(actor, "person", None), "user", None)
        return actor, user
    membership = getattr(actor, "membership", None)
    if isinstance(membership, Membership):
        user = getattr(getattr(membership, "person", None), "user", None)
        return membership, user
    # Treat as a User-like object.
    user = actor
    return None, user


def _content_label(content: Any, override: str | None = None) -> str:
    """Stable string identifier for ``content_type``.

    Order of preference: explicit override, ``content._audit_content_type_label()``,
    snake-case of the class name (matches the pattern used by
    :class:`OrderableContent._content_type_label`).
    """
    if override:
        return override
    method = getattr(content, "_audit_content_type_label", None) or getattr(
        content, "_content_type_label", None,
    )
    if callable(method):
        return method()
    name = type(content).__name__
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def _org_program(content: Any) -> tuple[Any, Any]:
    """Resolve ``(organization, program)`` from a duck-typed content row.

    Falls back, in order, to:

    1. Direct ``.organization`` / ``.program`` attributes.
    2. ``.organization_id`` / ``.program_id`` (looked up via the model managers).
    3. Optional ``_audit_organization()`` / ``_audit_program()`` hooks on the
       content model -- used by rows like :class:`Supervision` whose org
       is derived (``supervisor_membership.program.organization``) rather
       than stored directly.
    """
    org = getattr(content, "organization", None)
    program = getattr(content, "program", None)
    if org is None and getattr(content, "organization_id", None):
        from bunk_logs.core.models import Organization

        org = Organization.objects.filter(pk=content.organization_id).first()
    if program is None and getattr(content, "program_id", None):
        from bunk_logs.core.models import Program

        program = Program.all_objects.filter(pk=content.program_id).first()
    if org is None:
        hook = getattr(content, "_audit_organization", None)
        if callable(hook):
            org = hook()
    if program is None:
        hook = getattr(content, "_audit_program", None)
        if callable(hook):
            program = hook()
    return org, program


def _write(
    *,
    event_type: str,
    actor: Any,
    content: Any,
    content_type: str | None = None,
    content_id=None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    reason_note: str = "",
    is_admin_override: bool = False,
    metadata: dict | None = None,
) -> AuditEvent:
    actor_membership, actor_user = _resolve_actor(actor)
    org, program = _org_program(content)
    if org is None:
        msg = (
            "audit._write: cannot determine organization for content "
            f"{content!r}; helpers require a content row with an .organization"
            " or .organization_id attribute."
        )
        raise ValueError(msg)
    if content_id is None:
        content_id = getattr(content, "id", None) or getattr(content, "pk", None)
    if content_id is None:
        msg = "audit._write: cannot determine content_id from content row."
        raise ValueError(msg)
    return AuditEvent.all_objects.create(
        event_type=event_type,
        actor_membership=actor_membership,
        actor_user=actor_user,
        content_type=_content_label(content, content_type),
        content_id=str(content_id),
        organization=org,
        program=program,
        before_state=before_state or {},
        after_state=after_state or {},
        reason_note=reason_note or "",
        is_admin_override=bool(is_admin_override),
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Public helpers (the nine documented in the step prompt)
# ---------------------------------------------------------------------------


def created(actor: Any, content: Any, *, after_state: dict | None = None,
            content_type: str | None = None, metadata: dict | None = None) -> AuditEvent:
    """Record content creation (Story 4, 27, 41 for reflections; supervisions; orders).

    ``after_state`` is optional but recommended; it lets the audit consumer
    show what the row looked like at creation without joining back to the
    content table (helpful when the content row is later edited).
    """
    return _write(
        event_type=AuditEvent.EventType.CREATED,
        actor=actor,
        content=content,
        content_type=content_type,
        after_state=after_state,
        metadata=metadata,
    )


def edited(actor: Any, content: Any, before: dict, after: dict, *,
           content_type: str | None = None, metadata: dict | None = None) -> AuditEvent:
    """Record an in-window edit by the original author.

    Use ``override_edit`` instead when an Admin edits content authored by
    another role -- that path also sets ``is_admin_override=True``.
    """
    return _write(
        event_type=AuditEvent.EventType.EDITED,
        actor=actor,
        content=content,
        content_type=content_type,
        before_state=before,
        after_state=after,
        metadata=metadata,
    )


def state_changed(actor: Any, content: Any, before_state: str | dict, after_state: str | dict,
                  *, note: str = "", content_type: str | None = None,
                  metadata: dict | None = None) -> AuditEvent:
    """Record an order/ticket/flag state transition.

    ``before_state`` / ``after_state`` accept either a plain string
    (e.g. ``"new"`` -> ``"in_progress"``) or a dict if the caller wants to
    capture richer context. Strings are wrapped to ``{"status": <s>}``.
    """
    if isinstance(before_state, str):
        before_state = {"status": before_state}
    if isinstance(after_state, str):
        after_state = {"status": after_state}
    return _write(
        event_type=AuditEvent.EventType.STATE_CHANGED,
        actor=actor,
        content=content,
        content_type=content_type,
        before_state=before_state,
        after_state=after_state,
        reason_note=note,
        metadata=metadata,
    )


def deactivated(actor: Any, content: Any, *, reason: str = "",
                before_state: dict | None = None, after_state: dict | None = None,
                content_type: str | None = None,
                metadata: dict | None = None) -> AuditEvent:
    """Record a Membership / Supervision end-date or deactivation."""
    return _write(
        event_type=AuditEvent.EventType.DEACTIVATED,
        actor=actor,
        content=content,
        content_type=content_type,
        before_state=before_state,
        after_state=after_state,
        reason_note=reason,
        metadata=metadata,
    )


def reactivated(actor: Any, content: Any, *, reason: str = "",
                before_state: dict | None = None, after_state: dict | None = None,
                content_type: str | None = None,
                metadata: dict | None = None) -> AuditEvent:
    """Record reactivation of a previously deactivated Membership / Supervision."""
    return _write(
        event_type=AuditEvent.EventType.REACTIVATED,
        actor=actor,
        content=content,
        content_type=content_type,
        before_state=before_state,
        after_state=after_state,
        reason_note=reason,
        metadata=metadata,
    )


def override_edit(actor: Any, content: Any, before: dict, after: dict, *, reason: str,
                  content_type: str | None = None,
                  metadata: dict | None = None) -> AuditEvent:
    """Admin-override edit path (Story 59). ``reason`` is mandatory."""
    if not reason or not reason.strip():
        msg = "audit.override_edit: reason is required."
        raise ValueError(msg)
    return _write(
        event_type=AuditEvent.EventType.OVERRIDE_EDIT,
        actor=actor,
        content=content,
        content_type=content_type,
        before_state=before,
        after_state=after,
        reason_note=reason,
        is_admin_override=True,
        metadata=metadata,
    )


def override_close(actor: Any, content: Any, *, reason: str,
                   before_state: dict | None = None, after_state: dict | None = None,
                   content_type: str | None = None,
                   metadata: dict | None = None) -> AuditEvent:
    """Admin closed an order/ticket without the fulfilling role's normal path."""
    if not reason or not reason.strip():
        msg = "audit.override_close: reason is required."
        raise ValueError(msg)
    return _write(
        event_type=AuditEvent.EventType.OVERRIDE_CLOSE,
        actor=actor,
        content=content,
        content_type=content_type,
        before_state=before_state,
        after_state=after_state,
        reason_note=reason,
        is_admin_override=True,
        metadata=metadata,
    )


def override_resolve(actor: Any, content: Any, *, reason: str,
                     before_state: dict | None = None, after_state: dict | None = None,
                     content_type: str | None = None,
                     metadata: dict | None = None) -> AuditEvent:
    """Admin resolved a flag normally resolvable by another role."""
    if not reason or not reason.strip():
        msg = "audit.override_resolve: reason is required."
        raise ValueError(msg)
    return _write(
        event_type=AuditEvent.EventType.OVERRIDE_RESOLVE,
        actor=actor,
        content=content,
        content_type=content_type,
        before_state=before_state,
        after_state=after_state,
        reason_note=reason,
        is_admin_override=True,
        metadata=metadata,
    )


def audit_view(actor: Any, target_content: Any, *, content_type: str | None = None,
               metadata: dict | None = None) -> AuditEvent:
    """Meta-audit: an Admin viewed the audit trail for ``target_content``.

    Per Story 59 criterion 10 -- the audit log itself is an audited surface.
    """
    return _write(
        event_type=AuditEvent.EventType.AUDIT_VIEW,
        actor=actor,
        content=target_content,
        content_type=content_type,
        metadata=metadata,
    )


def export(actor: Any, content_query: dict, *, organization=None,
           program=None, metadata: dict | None = None) -> AuditEvent:
    """Record a CSV export. ``content_query`` is captured so reviewers can
    reproduce which rows were exported (filter params, date range, etc.).

    Unlike the other helpers, exports aren't tied to a single content row, so
    callers pass ``organization`` (and optionally ``program``) explicitly and
    we write a synthetic ``content_type='export'`` row using a fresh UUID
    drawn from the model's ``id`` default.
    """
    if organization is None:
        msg = "audit.export: organization is required."
        raise ValueError(msg)
    actor_membership, actor_user = _resolve_actor(actor)
    return AuditEvent.all_objects.create(
        event_type=AuditEvent.EventType.EXPORT,
        actor_membership=actor_membership,
        actor_user=actor_user,
        content_type="export",
        organization=organization,
        program=program,
        after_state={"query": content_query or {}},
        metadata=metadata or {},
    )
