import os
import re
import subprocess
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

PHASE_NAMES = {
    0: "Setup & Context",
    1: "Codebase Cleanup",
    2: "Core Multi-tenant Models",
    3: "Crane Lake Features",
    4: "Temple Beth-El Onboarding",
    5: "Historical Data Migration",
    6: "Legacy Deprecation",
}

SKIP_FILES = {"prefix.md", "0_0_context_prompt.md"}

# When the deliverable merged under a later step's commit (e.g. 1_5 doc in 1_6 PR),
# git log main will not mention the earlier step id — treat as done if these paths exist on main.
STEP_COMPLETION_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "1_5": ("docs/api-consolidation-plan.md",),
}


def _backend_dir() -> Path:
    return Path(settings.BASE_DIR).resolve()


def _git_cwd() -> Path:
    """Directory that contains the repo .git (used for git log / cat-file)."""
    raw_env = os.environ.get("BUNKLOGS_REPO_ROOT", "").strip()
    if raw_env:
        er = Path(raw_env).resolve()
        if (er / ".git").exists():
            return er
    backend = _backend_dir()
    if (backend.parent / ".git").exists():
        return backend.parent
    if (backend / ".git").exists():
        return backend
    container = Path("/repo")
    if (container / ".git").exists():
        return container
    return backend.parent


def _git_mainline_ref() -> str:
    """Ref treated as 'main' for log/cat-file (CI often has no local ``main``, only ``origin/main``)."""
    cwd = str(_git_cwd())
    for candidate in ("main", "origin/main"):
        result = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "--verify", candidate],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    return "HEAD"


def _migration_prompts_dir() -> Path | None:
    """Where migration_prompts/*.md live (monorepo sibling, bundled under backend, or env override)."""
    raw_env = os.environ.get("BUNKLOGS_REPO_ROOT", "").strip()
    if raw_env:
        mp = Path(raw_env).resolve() / "migration_prompts"
        if mp.is_dir():
            return mp
    backend = _backend_dir()
    for cand in (backend / "migration_prompts", backend.parent / "migration_prompts"):
        if cand.is_dir():
            return cand
    container = Path("/repo")
    if (container / "migration_prompts").is_dir():
        return container / "migration_prompts"
    return None


def _run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=str(_git_cwd()),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _parse_step_id(filename: str) -> tuple[str, int, int]:
    """Return (step_id, phase, sort_key) from a filename like '1_1_drop_unused_ninja.md'."""
    stem = Path(filename).stem
    m = re.match(r"^(\d+)_(\d+)", stem)
    if m:
        phase = int(m.group(1))
        step_num = int(m.group(2))
        return f"{phase}_{step_num}", phase, step_num
    m2 = re.match(r"^(\d+)_", stem)
    if m2:
        phase = int(m2.group(1))
        return stem, phase, 0
    return stem, 0, 0


def _parse_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    for line in text.splitlines():
        stripped = line.lstrip("# ").strip()
        if stripped:
            return stripped
    return path.stem


def _artifacts_satisfied_on_main(step_id: str) -> bool:
    rels = STEP_COMPLETION_ARTIFACTS.get(step_id)
    if not rels:
        return False
    base = _git_mainline_ref()
    cwd = str(_git_cwd())
    for rel in rels:
        result = subprocess.run(  # noqa: S603
            ["git", "cat-file", "-e", f"{base}:{rel}"],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return False
    return True


def _step_aliases(step_id: str) -> list[str]:
    """Return all textual forms a step might appear as (e.g. '3_17' and '3.17')."""
    return [step_id, step_id.replace("_", ".")]


def _determine_status(step_id: str, main_log: str, branch_names: set, merged_branches: set) -> tuple[str, str | None]:
    """Return (status, branch_name_or_None)."""
    for alias in _step_aliases(step_id):
        if re.search(rf"\b{re.escape(alias)}(?![0-9])", main_log):
            return "completed", None
    if _artifacts_satisfied_on_main(step_id):
        return "completed", None
    for branch in merged_branches:
        if branch in ("main", "HEAD"):
            continue
        if any(alias in branch for alias in _step_aliases(step_id)):
            return "completed", None
    for branch in branch_names - merged_branches:
        if any(alias in branch for alias in _step_aliases(step_id)):
            return "in_progress", branch
    return "pending", None


@api_view(["GET"])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def migration_status(request):
    if not request.user.is_staff:
        return Response(
            {
                "error": "Staff only",
                "steps": [],
                "git_available": False,
                "has_uncommitted_changes": False,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    prompts_dir = _migration_prompts_dir()
    if not prompts_dir:
        return Response(
            {
                "error": "migration_prompts directory not accessible",
                "steps": [],
                "git_available": False,
                "has_uncommitted_changes": False,
                "prompts_path_checked": str(_backend_dir() / "migration_prompts"),
            },
            status=status.HTTP_200_OK,
        )

    files = sorted(f for f in prompts_dir.glob("*.md") if f.name not in SKIP_FILES)

    mainline = _git_mainline_ref()
    main_log = _run_git(["log", mainline, "--oneline"])
    all_branches_raw = _run_git(["branch", "--all"])
    merged_raw = _run_git(["branch", "--all", "--merged", mainline])
    git_status = _run_git(["status", "--porcelain"])
    git_available = bool(all_branches_raw)

    def _parse_branches(raw: str) -> set:
        names = set()
        for line in raw.splitlines():
            name = line.strip().lstrip("* ").strip()
            if " -> " in name:
                continue
            if "remotes/origin/" in name:
                name = name.split("remotes/origin/")[-1]
            names.add(name)
        return names

    branch_names = _parse_branches(all_branches_raw)
    merged_branches = _parse_branches(merged_raw)

    steps = []
    for path in files:
        step_id, phase, step_num = _parse_step_id(path.name)
        title = _parse_title(path)
        step_status, branch = _determine_status(step_id, main_log, branch_names, merged_branches)
        steps.append({
            "id": step_id,
            "phase": phase,
            "phase_name": PHASE_NAMES.get(phase, f"Phase {phase}"),
            "step_num": step_num,
            "file": path.name,
            "title": title,
            "status": step_status,
            "branch": branch,
        })

    steps.sort(key=lambda s: (s["phase"], s["step_num"], s["file"]))

    return Response({
        "steps": steps,
        "git_available": git_available,
        "has_uncommitted_changes": bool(git_status),
        "repo_root": str(_git_cwd()),
        "migration_prompts_dir": str(prompts_dir),
    })
