# `atomic_dag.streaming` — Public Protocol

**Status:** Phase 3.B specification · Sprint 3 · FM-10 closure
**Source:** `src/atomic_dag/streaming.py` (implemented in 3.C)
**Authority:** ADR-007-sprint-3-fm10-streaming
**Constrained by:** ADR-003 §Lesson 3 (operation ordering); ADR-006 D1/D2/D4/D11 (patterns reused); ADR-004 (writer.py — I3: not modified)

This document specifies the observable contract of the `streaming` module before any production implementation exists. `streaming.py` (Phase 3.C) must satisfy every clause here. Where this document and ADR-007 diverge, ADR-007 wins.

---

## 1. Public surface

The module exposes exactly these public names. Everything else is private.

```python
tick_streaming(project: Path, event: StreamEvent) -> TickResult
advance_cursor(state_path: Path, new_cursor: str) -> None
StreamEvent        # frozen dataclass (input)
TickResult         # frozen dataclass (output)
StreamCursorMismatchError  # exception
```

---

## 2. `StreamEvent` (input)

A frozen dataclass representing a single streaming event.

```python
@dataclass(frozen=True)
class StreamEvent:
    event_id: str               # unique event identifier (ULID or UUID)
    ts: str                     # ISO-8601 UTC, source-provided (NOT auto-stamped)
    payload: dict[str, Any]     # opaque event-specific data; logged in WAL verbatim
    expected_cursor_from: str   # cursor value expected in state.json BEFORE the tick
```

`expected_cursor_from` is the falsifiability anchor on the input side: a caller must declare what cursor position they expect, enabling the system to detect out-of-order or duplicated delivery before mutating state.

---

## 3. `TickResult` (output)

A frozen dataclass. Truthiness (`__bool__`) equals `success`.

```python
@dataclass(frozen=True)
class TickResult:
    event_id: str
    advanced_cursor_from: str   # cursor value in state.json before the tick
    advanced_cursor_to: str     # cursor value in state.json after the tick
    wal_event_logged: bool       # True iff a WAL entry was written this call
    idempotent_replay: bool      # True iff event_id was already in WAL (replay)
    def __bool__(self) -> bool: return not self.idempotent_replay or self.advanced_cursor_to != ""
```

`advanced_cursor_from` and `advanced_cursor_to` are **mandatory fields** — they are the runtime falsifiability anchor. A `TickResult` where `advanced_cursor_from == advanced_cursor_to` and `idempotent_replay == False` indicates FM-10 is present and must be treated as a bug.

---

## 4. `tick_streaming(project, event) → TickResult`

Processes one streaming event and **guarantees** a call to `advance_cursor`.

### Post-condition (FM-10 fix, ADR-007 D7)

> After a successful non-idempotent tick:
> `json.loads((project / "state.json").read_text())["cursor"] == result.advanced_cursor_to`

This post-condition is the regression invariant. `tests/test_fm10_regression.py` tests it directly.

### Operation ordering (ADR-007 D1)

1. Parse `state.json` → `current_cursor`
2. Validate `event.expected_cursor_from == current_cursor` → raises `StreamCursorMismatchError` if not equal
3. Check idempotency: if `event.event_id` already in WAL → return `TickResult(idempotent_replay=True)` with **zero** disk writes and **zero** new WAL entries
4. Compute `new_cursor` (lexicographic increment of `current_cursor`)
5. **`advance_cursor(state_path, new_cursor)`** ← THE FM-10 FIX (mandatory, not optional)
6. `wal.log_event(project, {...})` — SINGLE event, AFTER `advance_cursor` (D11: disk leads, WAL confirms)
7. Return `TickResult(idempotent_replay=False, wal_event_logged=True, ...)`

### CLI invocation (Phase 3.E — DA-3: separate subcommand, not a flag)

```
atomic-dag --project PATH stream [--events-file FILE] [--json]
```

- Reads a sequence of `StreamEvent` as JSONL from `--events-file` or stdin.
  Each line: `{"event_id","ts","payload","expected_cursor_from"}`.
- Calls `tick_streaming(project, StreamEvent(**line))` for each event, in
  order; stops at the first failure.
- Text output: `stream evt-001: C-001 -> C-002` per event (or
  ` (idempotent replay, no-op)` suffix), then
  `processed N events, cursor now C-XXX`.
- `--json`: `{"results": [TickResult...], "processed": N, "final_cursor": "..."}`.

### Exit codes (CLI — ADR-007 D5)

| Code | Condition |
|---|---|
| `0` | all ticks processed successfully (including idempotent replay) |
| `1` | business error: cursor mismatch (`StreamCursorMismatchError`) |
| `2` | structural error: malformed JSONL, missing `state.json`, I/O failure |

### Error behavior

- `StreamCursorMismatchError`: raised before any disk write; state.json is unchanged
- `OSError` / I/O failures: may leave partial state; Sprint 5 `reconcile` recovers
- FSM-invalid actions: propagated as `StreamCursorMismatchError` or exit 1 per D5

---

## 5. `advance_cursor(state_path, new_cursor) → None`

Atomic mutation of the `cursor` field in `state.json`.

```python
def advance_cursor(state_path: Path, new_cursor: str) -> None:
    state = json.loads(state_path.read_text())
    state["cursor"] = new_cursor
    writer.write_atomic(state_path, json.dumps(state, indent=2))
```

- Uses `writer.write_atomic` (tmp+fsync+rename — ADR-004; **I3: `writer.py` not modified**)
- **Pure w.r.t. side effects beyond the target file**: no WAL entry, no other disk writes
- Can be unit-tested in isolation (no I/O beyond `state_path`)
- All other fields in `state.json` are preserved; only `cursor` is updated

---

## 6. `StreamCursorMismatchError`

```python
class StreamCursorMismatchError(Exception):
    """Raised when event.expected_cursor_from != state.cursor."""
```

Indicates cursor divergence — must not be silenced. Callers that catch this error must either reconcile state (Sprint 5 `reconcile` command) or abort the streaming run. Swallowing the error silently would re-introduce FM-10 semantics.

---

## 7. WAL schema: `streaming_tick`

```json
{
  "ts": "<ISO-8601 UTC, auto-stamped by wal.log_event>",
  "tipo": "streaming_tick",
  "event_id": "<str — unique per event>",
  "cursor_from": "<str — cursor before tick>",
  "cursor_to":   "<str — cursor after tick>",
  "event_payload": { }
}
```

`event_id`, `cursor_from`, and `cursor_to` are **non-optional** — the regression invariant D7 reads `cursor_to` to verify the on-disk state.json matches. `event_payload` is logged verbatim (no redaction, no truncation).

---

## 8. `state.json` schema

Introduced in Sprint 3 as the operational cursor store:

```json
{
  "cursor": "<atomic_id of the last successfully ticked atom, or '<start>' if none>",
  "updated_at": "<ISO-8601 UTC>"
}
```

> **Path:** `state.json` lives at the project root (`project / "state.json"`).
> `.atomic-dag/` holds only `wal.jsonl`. (Errata 0.5a: §8 earlier said
> `.atomic-dag/state.json`; §5/§10 are authoritative — root. `streaming.py`
> implements root; this aligns §8 to §5/§10. Docs-only consistency fix, no
> behavioural change.)

This file is **purpose-narrow**: it stores only the streaming cursor pointer, not atom states (those remain in `.md` frontmatter). This is consistent with ADR-006's rejection of `state.json`-as-atom-state.

---

## 9. Idempotency (ADR-007 D3)

Given the same `event_id` is submitted twice:
- First call: normal processing, `TickResult(idempotent_replay=False, wal_event_logged=True)`
- Second call: WAL already has the entry → `TickResult(idempotent_replay=True, wal_event_logged=False)`
- After second call: `read_events(wal_path)` returns a list of length 1 (not 2)
- `state.json` cursor is unchanged by the replay call

---

## 10. Usage example

```python
from pathlib import Path
from atomic_dag.streaming import tick_streaming, StreamEvent

event = StreamEvent(
    event_id="evt-001",
    ts="2026-05-30T18:00:00Z",
    payload={"action": "advance", "source": "llm-session-A"},
    expected_cursor_from="C-042",
)

result = tick_streaming(Path("./my-project"), event)

# Post-condition: cursor advanced on disk
# result.advanced_cursor_to == "C-043"
# state.json["cursor"] == "C-043"
# WAL has one streaming_tick entry with cursor_from="C-042", cursor_to="C-043"
```

---

## 11. Falsifiability note (D13 / ADR-007 §0)

The term *falsifiable* in this document is Popperian (1934): a claim is falsifiable when an experiment could refute it if false. The post-condition of `tick_streaming` is falsifiable in this sense: `test_fm10_regression.py::TestFM10Regression::test_cursor_advances_after_tick` is the experiment. Remove `advance_cursor(...)` from `tick_streaming` and the test fails — that failure is the refutation. The test passing means the post-condition survived an explicit attempt at refutation, which is what corroborates the FM-10 closure claim.
