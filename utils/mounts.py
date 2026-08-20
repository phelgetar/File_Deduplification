#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: mounts.py
# Purpose: Ensure network volumes are mounted before a run starts
#
# Description:
# A scan whose source is not actually mounted is worse than one that
# fails: /Volumes/home resolves to an empty directory, the scan finds
# nothing, and with --use-db the run looks like a successful pass over
# a volume that has lost all its files. With --execute the failure mode
# is worse still — the destination path exists locally, so files are
# copied onto the boot disk instead of the NAS.
#
# The check is therefore os.path.ismount(), not path.exists(): an
# unmounted mount point is usually still a real, empty directory.
#
# Mounting goes through `osascript ... mount volume`, which is the
# macOS-native path: it uses the credentials already in the login
# Keychain, needs no sudo, and mounts the share at /Volumes/<name>.
# No credential is read, stored, or logged by this module.
#
# Author: Tim Canady
# Created: 2026-08-18
#
# Version: 0.1.0
# Last Modified: 2026-08-18 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-18): Initial mount preflight — Tim Canady
###################################################################

from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Volumes this project expects, and where to get them.
#
# Override the server without editing code:  WORKBENCH_MOUNT_HOST=nas.local
# Override the protocol:                     WORKBENCH_MOUNT_SCHEME=afp
# Skip the whole preflight:                  WORKBENCH_NO_AUTOMOUNT=1
#
# SMB is the default because these are Synology-style share names and
# SMB is what macOS negotiates with them; afp and nfs also work here if
# your server prefers them.
DEFAULT_HOST = os.getenv("WORKBENCH_MOUNT_HOST", "canome")
DEFAULT_SCHEME = os.getenv("WORKBENCH_MOUNT_SCHEME", "smb")

REQUIRED_SHARES = ("home", "homes")

# How long to wait for one mount. A powered-off or off-subnet server
# would otherwise hang the run before it printed anything.
MOUNT_TIMEOUT_SECONDS = 45


def required_mounts(host: str = None, scheme: str = None) -> Dict[str, str]:
    """{mount point -> source URL} for the volumes this project needs."""
    host = host or DEFAULT_HOST
    scheme = scheme or DEFAULT_SCHEME
    return {f"/Volumes/{share}": f"{scheme}://{host}/{share}"
            for share in REQUIRED_SHARES}


def is_mounted(path) -> bool:
    """True only if `path` is an actual mount point.

    Deliberately not path.exists(): an unmounted /Volumes/home is
    frequently a leftover empty directory, and treating that as present
    is exactly the failure this module exists to prevent.
    """
    try:
        return os.path.ismount(str(path))
    except OSError:
        return False


# osascript surfaces mount failures as bare OSStatus codes. These are
# the ones that actually come up, translated into the thing to go check.
_ERROR_HINTS = {
    "-5016": ("server unreachable, or that share does not exist on it — "
              "check the host is awake and the share name is right"),
    "-128": ("no saved credentials — mount it once in Finder and tick "
             "'Remember this password in my keychain'"),
    "-35": "the server responded but the share was not found",
    "-36": "I/O error talking to the server",
    "-1": "generic failure — try mounting it once in Finder to see the real error",
}


def _explain(reason: str) -> str:
    """A parenthetical hint for a known OSStatus code, or nothing."""
    for code, hint in _ERROR_HINTS.items():
        if code in reason:
            return f" ({hint})"
    return ""


def mount_volume(url: str, mount_point: str,
                 timeout: int = MOUNT_TIMEOUT_SECONDS) -> Optional[str]:
    """Mount `url`. Returns None on success, or a reason on failure.

    Uses the Keychain via osascript rather than mount_smbfs so that no
    credential passes through this process, and so no sudo is needed.
    """
    logger.info(f"📡 Mounting {url} …")
    try:
        result = subprocess.run(
            ["osascript", "-e", f'mount volume "{url}"'],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return (f"timed out after {timeout}s — the server may be off, "
                f"asleep, or on another network")
    except OSError as e:
        return f"could not run osascript: {e}"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        reason = detail[-1] if detail else f"exit code {result.returncode}"
        return f"{reason}{_explain(reason)}"

    # osascript can report success before the mount is visible.
    for _ in range(10):
        if is_mounted(mount_point):
            return None
        time.sleep(0.5)
    return f"reported success but {mount_point} is still not a mount point"


def ensure_mounts(mounts: Dict[str, str] = None,
                  auto_mount: bool = True) -> List[str]:
    """Make sure every required volume is mounted.

    Returns a list of human-readable problems; empty means everything is
    ready. Callers should treat a non-empty result as fatal — continuing
    would scan or write to the wrong filesystem.
    """
    if os.getenv("WORKBENCH_NO_AUTOMOUNT"):
        logger.info("⏭️  Mount preflight skipped (WORKBENCH_NO_AUTOMOUNT set)")
        return []

    mounts = mounts if mounts is not None else required_mounts()
    problems: List[str] = []

    for mount_point, url in mounts.items():
        if is_mounted(mount_point):
            logger.info(f"✅ {mount_point} is mounted")
            continue

        if not auto_mount:
            problems.append(f"{mount_point} is not mounted (mount it from {url})")
            continue

        reason = mount_volume(url, mount_point)
        if reason is None:
            logger.info(f"✅ Mounted {mount_point} from {url}")
        else:
            problems.append(f"{mount_point}: could not mount {url} — {reason}")

    return problems


def describe() -> str:
    """One-line status for each required volume, for --show-mounts."""
    lines = []
    for mount_point, url in required_mounts().items():
        state = "mounted" if is_mounted(mount_point) else "NOT mounted"
        exists = Path(mount_point).exists()
        note = ""
        if not is_mounted(mount_point) and exists:
            note = "  ⚠️  path exists but is not a mount — a run would " \
                   "silently use local disk"
        lines.append(f"  {mount_point:<18} {state:<12} <- {url}{note}")
    return "\n".join(lines)


def unmounted_volume_for(path) -> Optional[str]:
    """The /Volumes mount point `path` needs, if it is not mounted.

    Generic on purpose: it protects any external volume, not just the
    ones in REQUIRED_SHARES. Cheap and offline — a stat, no network — so
    it is safe to call on every run, including from the web UI.
    """
    try:
        resolved = Path(path).expanduser()
    except (OSError, RuntimeError):
        return None

    parts = resolved.parts
    # ("/", "Volumes", "<name>", ...)
    if len(parts) < 3 or parts[1] != "Volumes":
        return None

    mount_point = str(Path(parts[0], parts[1], parts[2]))
    return None if is_mounted(mount_point) else mount_point
