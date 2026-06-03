"""build_dashboard.py — regenerate the volatile sections of docs/dashboard.html.

Closes the I-DASH invariant at level N2: the section that goes stale every single
phase — the meta header (HEAD SHA + tag + sprint phase descriptor) — is regenerated
from the canonical source (docs/STATUS.md) instead of being bumped by hand, and a
`--check` mode lets CI fail when the dashboard drifts from STATUS.

SCOPE (surgical, per the 4.E mandate + ADR/ROADMAP "N2"):
  - REGENERATED:  the `<!-- BUILD:meta ... -->` region (HEAD / tag / phase line).
    This is the section that defasa on literally every phase and is purely
    mechanical (derivable from STATUS.md). Automating it + the --check gate is
    the highest-value, zero-risk part of I-DASH mechanization.
  - PARSED-BUT-NOT-REWRITTEN:  `_parse_merge_timeline` and `_parse_debts` extract
    the timeline and debts data from STATUS.md / TECHNICAL_DEBT.md. They are
    tested and ready, but the dashboard's timeline and debts panels carry
    curated, filtered prose (only MERGE rows, bespoke one-line descriptions,
    a deliberately compacted debts subset) that diverges from the STATUS tables.
    Rewriting them from STATUS would normalize-away that curation, so per the
    mandate's §8 escalation clause this version does NOT rewrite them. A future
    phase can wire them once the STATUS-as-source normalization is decided.

NON-GOAL: regenerating the whole dashboard. The 5W1H sprint cards, CSS, and macro
narrative are hand-curated template and are preserved verbatim.

Usage:
    python scripts/build_dashboard.py            # rewrite the meta region in place
    python scripts/build_dashboard.py --check    # exit 1 if the meta region drifted
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DASHBOARD = REPO / "docs" / "dashboard.html"
STATUS = REPO / "docs" / "STATUS.md"
TECH_DEBT = REPO / "TECHNICAL_DEBT.md"

COMMIT_URL = "https://github.com/camillanapoles/atomic-dag-soc/commit"

MARKER = re.compile(
    r"(?P<start><!-- BUILD:(?P<name>[\w-]+) START -->)"
    r"(?P<body>.*?)"
    r"(?P<end><!-- BUILD:(?P=name) END -->)",
    re.DOTALL,
)


# --------------------------------------------------------------------------- #
# Parsing — read the canonical sources                                        #
# --------------------------------------------------------------------------- #


def parse_status_head(status_text: str) -> tuple[str, str]:
    """Return (short_sha, descriptor) from STATUS.md's '**HEAD:**' line.

    Line shape: ``- **HEAD:** `bb54224` (Sprint 4 em curso; ...)``
    The descriptor is the parenthetical text after the SHA (may be empty).
    """
    m = re.search(r"\*\*HEAD:\*\*\s*`([0-9a-f]+)`(?:\s*\(([^)]*)\))?", status_text)
    if not m:
        raise ValueError("STATUS.md: '**HEAD:**' line not found or malformed")
    return m.group(1), (m.group(2) or "").strip()


def parse_status_tag(status_text: str) -> tuple[str, str]:
    """Return (tag, qualifier) from STATUS.md's '**Tag mais recente:**' line.

    Line shape: ``- **Tag mais recente:** `v0.4.0-sprint3` (lightweight — D8; ...)``
    The qualifier is the leading clause of the first parenthetical, trimmed at
    the first ';' (so "(lightweight — D8; GitHub UI ...)" -> "lightweight — D8").
    Returns ("", "") if no tag line is present.
    """
    m = re.search(
        r"\*\*Tag mais recente:\*\*\s*`([^`]+)`(?:\s*\(([^)]*)\))?", status_text
    )
    if not m:
        return "", ""
    tag = m.group(1).strip()
    qualifier = (m.group(2) or "").split(";")[0].strip()
    return tag, qualifier


def parse_merge_timeline(status_text: str) -> list[dict[str, str]]:
    """Parse MERGE rows from STATUS.md's 'Fases pós-merge' table.

    Row shape: ``| [`sha`](url) | **4.C MERGE** | when | `message` |``
    Only rows whose phase ends in 'MERGE' are returned (the dashboard timeline
    shows merge-marks, not intermediate phase commits).
    """
    rows: list[dict[str, str]] = []
    row_re = re.compile(
        r"\|\s*\[`(?P<sha>[0-9a-f]+)`\]\([^)]+\)\s*\|\s*\*\*(?P<phase>[^*]+?)\*\*\s*"
        r"\|\s*(?P<when>[^|]*?)\s*\|\s*`?(?P<msg>[^|`]+?)`?\s*\|"
    )
    for m in row_re.finditer(status_text):
        phase = m.group("phase").strip()
        if not phase.endswith("MERGE"):
            continue
        rows.append(
            {
                "sha": m.group("sha"),
                "phase": phase,
                "when": m.group("when").strip(),
                "message": m.group("msg").strip(),
            }
        )
    return rows


def parse_debts(status_text: str) -> list[dict[str, str]]:
    """Parse the 'Dívidas registradas' table from STATUS.md.

    Returns one record per row: {id, status (open|closed), description}.
    A debt is 'closed' when its state cell mentions fechada / resolvida.
    Robust: rows that don't match the expected shape are skipped, not fatal.
    """
    debts: list[dict[str, str]] = []
    section = status_text.split("## Dívidas registradas", 1)
    if len(section) < 2:
        return debts
    body = section[1].split("\n## ", 1)[0]
    row_re = re.compile(
        r"\|\s*~{0,2}\*{0,2}(?P<id>[\w.-]+)\*{0,2}~{0,2}\s*\|\s*[^|]*\|\s*"
        r"(?P<desc>[^|]+?)\s*\|\s*(?P<state>[^|]+?)\s*\|"
    )
    for m in row_re.finditer(body):
        debt_id = m.group("id").strip()
        if debt_id in {"ID", ""}:  # header row
            continue
        state = m.group("state").lower()
        closed = "fechada" in state or "resolvida" in state
        debts.append(
            {
                "id": debt_id,
                "status": "closed" if closed else "open",
                "description": m.group("desc").strip(),
            }
        )
    return debts


# --------------------------------------------------------------------------- #
# Rendering — emit the volatile HTML                                          #
# --------------------------------------------------------------------------- #


def render_meta(status_text: str) -> str:
    """Render the inner of the <div class="meta"> block from STATUS.md."""
    sha, descriptor = parse_status_head(status_text)
    tag, qualifier = parse_status_tag(status_text)

    lines = [
        '  Branch <strong>main</strong> &middot;',
        f'  HEAD <a href="{COMMIT_URL}/{sha}">{sha}</a> &middot;',
    ]
    if tag:
        tag_suffix = f" ({qualifier})" if qualifier else ""
        lines.append(f"  Tag <strong>{tag}</strong>{tag_suffix} &middot;")
    if descriptor:
        lines.append(f"  {descriptor}")
    else:  # drop a trailing &middot; if there is no descriptor to follow it
        lines[-1] = lines[-1].removesuffix(" &middot;")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Build orchestration                                                         #
# --------------------------------------------------------------------------- #


def _rendered_sections(status_text: str) -> dict[str, str]:
    """Map of marker-name -> rendered inner HTML for the managed sections.

    Only `meta` is managed (rewritten) in this N2 version. `timeline` and
    `debts` are parsed (and tested) but intentionally not rewritten — see the
    module docstring.
    """
    return {"meta": render_meta(status_text)}


def regenerate(html: str, status_text: str) -> str:
    """Return `html` with every managed BUILD marker region rewritten."""
    sections = _rendered_sections(status_text)

    def _replace(m: re.Match[str]) -> str:
        name = m.group("name")
        if name in sections:
            return f"{m.group('start')}\n{sections[name]}\n{m.group('end')}"
        return m.group(0)  # unmanaged marker: leave untouched

    return MARKER.sub(_replace, html)


def build(check_only: bool = False) -> int:
    html = DASHBOARD.read_text(encoding="utf-8")
    status_text = STATUS.read_text(encoding="utf-8")
    new_html = regenerate(html, status_text)

    if check_only:
        if new_html != html:
            print(
                "dashboard.html is OUT OF DATE — run: python scripts/build_dashboard.py",
                file=sys.stderr,
            )
            return 1
        print("dashboard.html meta section is up to date")
        return 0

    if new_html != html:
        DASHBOARD.write_text(new_html, encoding="utf-8")
        sha, _ = parse_status_head(status_text)
        print(f"dashboard.html regenerated (HEAD {sha})")
    else:
        print("dashboard.html already up to date")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Regenerate the volatile meta section of docs/dashboard.html."
    )
    ap.add_argument(
        "--check", action="store_true", help="Exit 1 if the meta region drifted (CI)."
    )
    args = ap.parse_args(argv)
    return build(check_only=args.check)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
