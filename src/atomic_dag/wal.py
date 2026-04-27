"""
WAL Logger: append-only Write-Ahead Log in JSON Lines format.

Every state transition and significant event in the system is written
here as an immutable record. The WAL serves two purposes:

1. Audit: post-hoc analysis of what happened and when.
2. Recovery: reconstructing state by replaying events from a known point.

The file format is JSON Lines (jsonl): one JSON object per line,
append-only, UTF-8. This is the de-facto standard for structured logs
and works with standard Unix tools (grep, jq, tail).

This module is functional from Sprint 0 because its only dependency is
the standard library.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def log_event(wal_path: str | Path, event: dict[str, Any]) -> None:
    """
    Append an event to the WAL.

    The timestamp is added automatically in UTC ISO-8601 format if not
    already present. This respects the project-wide convention that all
    datetimes use ``timezone.utc``.

    Parameters
    ----------
    wal_path : str or Path
        Path to the WAL file. Created if it does not exist. Parent
        directory must already exist.
    event : dict
        Event payload. At minimum should include ``atom_id`` and
        ``event_type``; additional fields are free-form.

    Raises
    ------
    OSError
        If the WAL file cannot be opened in append mode.
    TypeError
        If the event dict contains non-JSON-serializable values.
    """
    if "timestamp" not in event:
        event = {"timestamp": datetime.now(tz=UTC).isoformat(), **event}

    # Serialize first so that a serialization error doesn't leave a
    # half-written line in the file.
    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"

    # Append mode is atomic at the line level on POSIX when writes are
    # smaller than PIPE_BUF (typically 4096 bytes), which is the case for
    # all reasonable event payloads.
    with open(wal_path, "a", encoding="utf-8") as f:
        f.write(line)


def read_events(wal_path: str | Path) -> list[dict[str, Any]]:
    """
    Read all events from a WAL file.

    Returns
    -------
    list of dict
        All events in the file, in the order they were written.
        An empty list if the file does not exist or is empty.
    """
    path = Path(wal_path)
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events
