import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

PHASE_NAMES = {
    0: "Setup & Context",
    1: "Codebase Cleanup",
    2: "Core Multi-tenant Models",
    3: "Crane Lake Features",
    4: "Temple Beth-El Onboarding",
    5: "Historical Data Migration",
    6: "Legacy Deprecation",
}

SKIP_FILES = {"prefix.md"}

# In the Docker container the repo root is mounted at /repo.
# In production (Render) BASE_DIR is backend/ so parent is the repo root.
_CONTAINER_REPO = Path("/repo")
_REPO_ROOT = _CONTAINER_REPO if (_CONTAINER_REPO / ".git").exists() else Path(settings.BASE_DIR).parent
PROMPTS_DIR = _REPO_ROOT / "migration_prompts"


def _run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
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
        # non-numeric second segment; use 0 as sort key so it sorts before 0_1
        return stem, phase, 0
    return stem, 0, 0


def _parse_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    for line in text.splitlines():
        stripped = line.lstrip("# ").strip()
        if stripped:
            return stripped
    return path.stem


def _determine_status(step_id: str, main_log: str, branch_names: set, merged_branches: set) -> tuple[str, str | None]:
    """Return (status, branch_name_or_None)."""
    # A step is completed if the step_id appears in a main-branch commit message.
    # Use (?![0-9]) instead of trailing \b because _ is a word char, so
    # \b1_2\b would NOT match "1_2_resolve_..." in commit messages.
    if re.search(rf"\b{re.escape(step_id)}(?![0-9])", main_log):
        return "completed", None
    # Or if a matching branch has been merged into main
    for branch in merged_branches:
        if step_id in branch and branch not in ("main", "HEAD"):
            return "completed", None
    # In-progress: a live unmerged branch exists that references this step
    for branch in branch_names - merged_branches:
        if step_id in branch:
            return "in_progress", branch
    return "pending", None


@require_GET
def migration_status(request):
    if not PROMPTS_DIR.exists():
        return JsonResponse({"error": "migration_prompts directory not accessible", "steps": []}, status=200)

    files = sorted(f for f in PROMPTS_DIR.glob("*.md") if f.name not in SKIP_FILES)

    main_log = _run_git(["log", "main", "--oneline"])
    all_branches_raw = _run_git(["branch", "--all"])
    merged_raw = _run_git(["branch", "--all", "--merged", "main"])
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
        status, branch = _determine_status(step_id, main_log, branch_names, merged_branches)
        steps.append({
            "id": step_id,
            "phase": phase,
            "phase_name": PHASE_NAMES.get(phase, f"Phase {phase}"),
            "step_num": step_num,
            "file": path.name,
            "title": title,
            "status": status,
            "branch": branch,
        })

    steps.sort(key=lambda s: (s["phase"], s["step_num"], s["file"]))

    return JsonResponse({
        "steps": steps,
        "git_available": git_available,
        "has_uncommitted_changes": bool(git_status),
        "repo_root": str(_REPO_ROOT),
    })
