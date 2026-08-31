#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: services.py
# Purpose: Is the rest of the local dev stack up?
#
# Description:
# The workbench is one of nine services on this machine, and it
# depends on two of them: MySQL for everything, Ollama for the local
# classification tier. When a scan produces nothing useful the cause
# is often a service that quietly died, and the answer is currently a
# terminal away.
#
# The list of services is NOT duplicated here. It is read out of
# start-services.sh, which already defines each one's port, label and
# URL, because a second copy is a copy that drifts — classify/extract.py
# sat a full minor version behind its original for exactly that reason.
#
# What is not borrowed is the checking. `start-services.sh status`
# takes ~770ms and spawns nine lsof processes, which is fine to type
# and far too slow for a panel that refreshes on a timer. A TCP connect
# to a loopback port answers the same question in microseconds.
#
# Author: Tim Canady
# Created: 2026-08-25
#
# Version: 1.0.0
# Last Modified: 2026-08-25 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-08-25): Initial service status probe — Tim Canady
###################################################################

from __future__ import annotations

import logging
import os
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
SCRIPT = Path(os.getenv("WORKBENCH_SERVICES_SCRIPT",
                        REPO.parent / "start-services.sh"))

# A loopback connect either succeeds immediately or the port is closed;
# this only has to be long enough to survive a busy machine.
CONNECT_TIMEOUT = 0.35


@dataclass
class Service:
    name: str
    label: str
    url: str
    port: Optional[int]
    up: bool = False
    # The workbench itself needs these two; a scan fails or silently
    # degrades without them, so the UI can say so rather than just
    # colouring a dot.
    required_by_workbench: bool = False


REQUIRED = {"mysql", "ollama"}

_cache: Optional[List[Service]] = None
_cache_mtime: float = 0.0


def _case_table(body: str, func: str) -> dict:
    """Pull `name) echo value ;;` pairs out of one shell function."""
    m = re.search(rf"^{func}\(\)\s*\{{(.*?)^\}}", body, re.S | re.M)
    if not m:
        return {}
    out = {}
    for name, value in re.findall(r'^\s*([\w-]+)\)\s*echo\s+"?([^";]*?)"?\s*;;',
                                  m.group(1), re.M):
        out[name] = value.strip()
    return out


def definitions() -> List[Service]:
    """Services as start-services.sh defines them, cached by its mtime."""
    global _cache, _cache_mtime
    try:
        mtime = SCRIPT.stat().st_mtime
    except OSError:
        if _cache is None:
            logger.info("No service script at %s — status panel disabled", SCRIPT)
        return _cache or []
    if _cache is not None and mtime == _cache_mtime:
        return _cache

    body = SCRIPT.read_text()
    order = re.search(r'^ALL_SERVICES="([^"]+)"', body, re.M)
    names = order.group(1).split() if order else []
    ports = _case_table(body, "svc_port")
    labels = _case_table(body, "svc_label")
    urls = _case_table(body, "svc_url")
    if not names or not labels:
        logger.warning("Could not parse services from %s — its format may have "
                       "changed; the status panel will be empty", SCRIPT)
        return []

    services = []
    for name in names:
        raw = ports.get(name, "")
        services.append(Service(
            name=name,
            label=labels.get(name, name),
            url=urls.get(name, ""),
            port=int(raw) if raw.isdigit() else None,
            required_by_workbench=name in REQUIRED,
        ))
    # Display order: the script's order is a start order, chosen so ports
    # are claimed deterministically. Alphabetical by label reads better in
    # a list somebody scans for a red dot.
    services.sort(key=lambda s: s.label.lower())
    _cache, _cache_mtime = services, mtime
    return services


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(CONNECT_TIMEOUT)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _running_in(pattern: str, directory: str) -> bool:
    """A process matching `pattern` whose working directory is `directory`.

    The directory is what makes this reliable. `pgrep -f` matches whole
    command lines, so anything that merely mentions the pattern counts —
    including this checker's own shell, and including sibling processes in
    its pipeline, which no amount of pid filtering excludes. A cwd of
    Jarheads.net is evidence; a matching string is not. This is how
    start-services.sh decides it too (pids_by_cwd).
    """
    try:
        found = subprocess.run(["pgrep", "-f", pattern],
                               capture_output=True, timeout=3, text=True)
    except (OSError, subprocess.SubprocessError):
        return False
    for pid in found.stdout.split():
        if not pid.strip().isdigit():
            continue
        try:
            out = subprocess.run(["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"],
                                 capture_output=True, timeout=3, text=True)
        except (OSError, subprocess.SubprocessError):
            continue
        if any(l.startswith("n") and l[1:] == directory
               for l in out.stdout.splitlines()):
            return True
    return False


# Services with no port need their own evidence. Kept beside the parser
# rather than in it: the script checks this one by working directory,
# which is not something a case table can express.
PORTLESS_CHECKS = {
    "jarheads-scheduler": (r"[Pp]ython.*scheduler\.py",
                           str(REPO.parent / "Jarheads.net")),
}


def _check(service: Service) -> Service:
    if service.port is not None:
        service.up = _port_open(service.port)
    else:
        check = PORTLESS_CHECKS.get(service.name)
        service.up = _running_in(*check) if check else False
    return service


def status() -> List[dict]:
    """Every service and whether it is up, probed concurrently."""
    services = definitions()
    if not services:
        return []
    with ThreadPoolExecutor(max_workers=min(16, len(services))) as pool:
        checked = list(pool.map(_check, services))
    return [{"name": s.name, "label": s.label, "url": s.url, "port": s.port,
             "up": s.up, "required": s.required_by_workbench} for s in checked]
