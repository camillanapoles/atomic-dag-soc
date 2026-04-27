# ADR-004: Atomic File Writes via tmp + fsync + rename

**Status:** Accepted (and validated by `test_atomic_write_survives_sigkill`)  
**Date:** 2026-04-20

## Context

The FM-02 failure mode in the SOC V4 FMEA stated, with RPN of 90, that the function `save_state_atomic` was not actually atomic despite its name. A naive write — `open(path, "w").write(content)` — leaves a window where the file is partially written. If the process crashes during that window, the file ends up corrupted, and on next startup the system reads inconsistent state. This is unacceptable for any system that claims to preserve invariants.

## Decision

All writes that must survive process death use the canonical POSIX-atomic pattern: write to a temporary file in the same directory, call `fsync` on the file descriptor, close the descriptor, and call `os.rename` to the final destination. The `rename` syscall is atomic when source and destination are on the same filesystem.

This is implemented in `src/atomic_dag/writer.py` as `write_atomic(target, content)`.

## Consequences

**Positive.** At every observable instant, the target file contains either the previous valid content or the new valid content. There is no observable intermediate state. Validated empirically by `test_atomic_write_survives_sigkill` which executes 50 iterations of "spawn writer, kill at random time, verify file integrity" and passes consistently.

**Negative.** Writes are slightly slower than direct writes due to the temp-file overhead and the fsync. For our workload (state files, atom updates) this is negligible — sub-millisecond on typical disks.

**Neutral.** The temp file naming convention `.{name}.{random}.tmp` is hidden by the leading dot so it does not appear in `ls` by default. Clean-up on error paths is enforced by `contextlib.suppress(OSError)` to ensure no orphans.

## Alternatives Considered

1. **Direct write.** Rejected because it is exactly the FM-02 failure being mitigated.
2. **File locking (flock).** Rejected because it does not solve atomicity — it only prevents concurrent writes — and adds cross-platform complexity (no flock on Windows).
3. **Embedded SQLite.** Rejected because it is overkill, introduces a binary format, and breaks the "documentation as code" principle that the system relies on.
