"""Tests for scripts/build_dashboard.py — parsing + idempotent regeneration.

The `--check` mode is the mechanized I-DASH gate: it must exit 0 when the
dashboard's meta region is in sync with STATUS.md, and 1 when it drifts.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "build_dashboard.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_dashboard", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_dashboard"] = module
    spec.loader.exec_module(module)
    return module


# --- CLI / idempotency ------------------------------------------------------


def test_check_passes_on_current_repo() -> None:
    """--check exits 0: the committed dashboard meta is in sync with STATUS."""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"dashboard meta out of date:\n{r.stdout}\n{r.stderr}"


def test_regenerate_is_idempotent() -> None:
    """Regenerating twice yields no further change (build by construction)."""
    mod = _load_module()
    html = mod.DASHBOARD.read_text(encoding="utf-8")
    status = mod.STATUS.read_text(encoding="utf-8")
    once = mod.regenerate(html, status)
    twice = mod.regenerate(once, status)
    assert once == twice
    # And the committed file is already at the fixed point:
    assert mod.regenerate(html, status) == html


# --- meta parsing + rendering ----------------------------------------------


def test_parse_status_head() -> None:
    mod = _load_module()
    sha, desc = mod.parse_status_head(
        "- **HEAD:** `bb54224` (Sprint 4 em curso; 4.E em PR)\n"
    )
    assert sha == "bb54224"
    assert desc == "Sprint 4 em curso; 4.E em PR"


def test_parse_status_head_no_descriptor() -> None:
    mod = _load_module()
    sha, desc = mod.parse_status_head("- **HEAD:** `abc1234`\n")
    assert sha == "abc1234"
    assert desc == ""


def test_parse_status_tag_trims_at_semicolon() -> None:
    mod = _load_module()
    tag, qual = mod.parse_status_tag(
        "- **Tag mais recente:** `v0.4.0-sprint3` (lightweight — D8; GitHub UI ...)\n"
    )
    assert tag == "v0.4.0-sprint3"
    assert qual == "lightweight — D8"


def test_render_meta_contains_head_and_tag() -> None:
    mod = _load_module()
    status = (
        "- **HEAD:** `bb54224` (Sprint 4 em curso)\n"
        "- **Tag mais recente:** `v0.4.0-sprint3` (lightweight — D8)\n"
    )
    out = mod.render_meta(status)
    assert "bb54224" in out
    assert "v0.4.0-sprint3" in out
    assert "(lightweight — D8)" in out
    assert "Sprint 4 em curso" in out


def test_render_meta_matches_committed_dashboard() -> None:
    """The committed dashboard meta region equals render_meta(STATUS)."""
    mod = _load_module()
    status = mod.STATUS.read_text(encoding="utf-8")
    html = mod.DASHBOARD.read_text(encoding="utf-8")
    expected_inner = mod.render_meta(status)
    m = mod.MARKER.search(html)
    assert m is not None and m.group("name") == "meta"
    assert m.group("body").strip("\n") == expected_inner


# --- timeline + debts parsers (parsed-but-not-rewritten; proven extractable) #


def test_parse_merge_timeline_filters_to_merges() -> None:
    mod = _load_module()
    sample = (
        "| [`bb54224`](https://x/bb54224) | **4.D MERGE** | 2026-06-01 | "
        "`Merge PR #22 — hello-soc` |\n"
        "| [`1de7072`](https://x/1de7072) | **2.K** | 2026-05-29 | "
        "`docs(2.k): not a merge row` |\n"
    )
    rows = mod.parse_merge_timeline(sample)
    assert len(rows) == 1  # the non-MERGE row is filtered out
    assert rows[0]["sha"] == "bb54224"
    assert rows[0]["phase"] == "4.D MERGE"
    assert "hello-soc" in rows[0]["message"]


def test_parse_debts_classifies_open_and_closed() -> None:
    mod = _load_module()
    status = (
        "## Dívidas registradas (pós-Sprint 2)\n\n"
        "| ID | Origem | Descrição | Estado |\n"
        "|---|---|---|---|\n"
        "| **D1** | `x` | algo aberto | aberta |\n"
        "| ~~D3~~ | y | algo | **fechada em `45161a8`** |\n"
        "| **TD-003** | z | FM-10 | **RESOLVIDA em 3.C** |\n"
        "\n## Próxima seção\n"
    )
    debts = mod.parse_debts(status)
    by_id = {d["id"]: d for d in debts}
    assert by_id["D1"]["status"] == "open"
    assert by_id["D3"]["status"] == "closed"
    assert by_id["TD-003"]["status"] == "closed"


def test_parse_debts_empty_when_section_absent() -> None:
    mod = _load_module()
    assert mod.parse_debts("no debts section here") == []
