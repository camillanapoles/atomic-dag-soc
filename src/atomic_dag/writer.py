"""
Atomic file writer implementing the tmp-file + fsync + rename pattern.

Why this matters
----------------
The FM-02 failure mode identified in the SOC V4 FMEA (RPN=90) stated that
'save_state_atomic' was not actually atomic despite its name. A naive
implementation that writes directly to the target file can leave a partial
write if the process is killed mid-write - producing corrupted state.

The POSIX-guaranteed technique below avoids that risk by writing to a temp
file first, fsyncing to ensure data hits physical storage, then performing
an atomic rename. At any moment, the target file contains either the old
content or the new content - never a mix.

This is the same technique used by databases, git itself, and any file
operation that must survive power loss.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def write_atomic(target: str | Path, content: str | bytes) -> None:
    """
    Write ``content`` to ``target`` atomically.

    Guarantees (on POSIX filesystems such as ext4, xfs, apfs, and NTFS on
    modern Windows):

    - If this function returns without exception, the file at ``target``
      contains exactly ``content``.
    - If the process crashes at any point during execution, the file at
      ``target`` contains either the content it had before this call, or
      exactly the new content. It NEVER contains partial data.

    Parameters
    ----------
    target : str or Path
        Destination file path. Parent directory must already exist.
    content : str or bytes
        Content to write. Strings are encoded as UTF-8.

    Raises
    ------
    OSError
        If the parent directory does not exist, the temp file cannot be
        created or written, fsync fails, or the atomic rename fails.
    """
    target_path = Path(target)
    target_dir = target_path.parent

    if not target_dir.is_dir():
        raise OSError(f"Target directory does not exist: {target_dir}")

    # Normalize to bytes. We do this BEFORE touching disk so that an
    # encoding error (impossible with utf-8 for valid str, but defensive)
    # fails without side-effects on the filesystem.
    data = content.encode("utf-8") if isinstance(content, str) else content

    # Create the temp file in the SAME directory as the target.
    # This is essential: os.rename is atomic only when source and target
    # are on the same filesystem. If the temp file were in /tmp while the
    # target is in /home, rename would fall back to copy+delete, losing
    # atomicity.
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=target_dir,
        prefix=f".{target_path.name}.",
        suffix=".tmp",
    )

    try:
        # Write all data. os.write may do partial writes under pressure,
        # so we loop until everything lands.
        remaining = data
        while remaining:
            written = os.write(tmp_fd, remaining)
            remaining = remaining[written:]

        # fsync forces the OS to flush its buffer cache to physical disk.
        # Without this, the OS may report the write as successful but the
        # data would live only in RAM - a power loss would lose it.
        os.fsync(tmp_fd)

    except Exception:
        # On error, close and unlink the temp file; never leave orphans.
        os.close(tmp_fd)
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    else:
        # Close the fd BEFORE rename. On Windows, rename fails if the
        # source file is still open. On POSIX this is unnecessary but
        # harmless.
        os.close(tmp_fd)

    # The atomic commit step. After this single syscall returns
    # successfully, target either points to the old inode (rename failed
    # with exception) or to the new inode (rename succeeded). There is no
    # intermediate observable state.
    os.rename(tmp_path, target_path)
