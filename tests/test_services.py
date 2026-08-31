#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: test_services.py
# Purpose: The service status panel
#
# Description:
# The service list is read out of start-services.sh rather than
# copied, because a copy drifts — classify/extract.py sat a full
# minor version behind its original for exactly that reason. These
# pin the parser against the script's real shape, and pin the
# portless check against the false positive that made a dead service
# look alive.
#
# Author: Tim Canady
# Created: 2026-08-25
#
# Version: 1.0.0
# Last Modified: 2026-08-25 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-08-25): Initial service status tests — Tim Canady
###################################################################

import socket
import textwrap
from pathlib import Path

import pytest

from core import services

SCRIPT = textwrap.dedent('''\
    #!/bin/bash
    ALL_SERVICES="backend mysql jarheads-scheduler"

    svc_port() {
      case "$1" in
        mysql) echo 3306 ;;
        backend) echo 8000 ;;
        jarheads-scheduler) echo "" ;;    # background job, no port
      esac
    }

    svc_label() {
      case "$1" in
        mysql) echo "MySQL" ;;
        backend) echo "usaccidents backend" ;;
        jarheads-scheduler) echo "jarheads scheduler" ;;
      esac
    }

    svc_url() {
      case "$1" in
        mysql) echo "mysql://127.0.0.1:3306" ;;
        backend) echo "http://127.0.0.1:8000" ;;
        jarheads-scheduler) echo "(background crawl, every 6h)" ;;
      esac
    }
    ''')


@pytest.fixture
def script(tmp_path, monkeypatch):
    path = tmp_path / "start-services.sh"
    path.write_text(SCRIPT)
    monkeypatch.setattr(services, "SCRIPT", path)
    monkeypatch.setattr(services, "_cache", None)
    monkeypatch.setattr(services, "_cache_mtime", 0.0)
    return path


def test_definitions_are_read_from_the_script(script):
    defs = {s.name: s for s in services.definitions()}
    assert set(defs) == {"mysql", "backend", "jarheads-scheduler"}
    assert defs["mysql"].port == 3306
    assert defs["backend"].label == "usaccidents backend"
    assert defs["mysql"].url == "mysql://127.0.0.1:3306"


def test_a_portless_service_parses_as_portless(script):
    assert {s.name: s.port for s in services.definitions()}["jarheads-scheduler"] is None


def test_the_workbench_marks_what_it_depends_on(script):
    """MySQL and Ollama are not just services here — a scan fails or
    silently degrades without them, so the UI says so."""
    defs = {s.name: s for s in services.definitions()}
    assert defs["mysql"].required_by_workbench is True
    assert defs["backend"].required_by_workbench is False


def test_listed_alphabetically_not_in_start_order(script):
    """The script's order is a start order, chosen so ports are claimed
    deterministically. A human scanning for a red dot wants A-Z."""
    labels = [s.label for s in services.definitions()]
    assert labels == sorted(labels, key=str.lower)


def test_a_missing_script_is_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(services, "SCRIPT", tmp_path / "absent.sh")
    monkeypatch.setattr(services, "_cache", None)
    monkeypatch.setattr(services, "_cache_mtime", 0.0)
    assert services.definitions() == []
    assert services.status() == []


def test_an_unparseable_script_is_not_an_error(tmp_path, monkeypatch):
    bad = tmp_path / "start-services.sh"
    bad.write_text("#!/bin/bash\necho hello\n")
    monkeypatch.setattr(services, "SCRIPT", bad)
    monkeypatch.setattr(services, "_cache", None)
    monkeypatch.setattr(services, "_cache_mtime", 0.0)
    assert services.definitions() == []


def test_port_probe_distinguishes_open_from_closed():
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        assert services._port_open(port) is True
    # closed as soon as the socket is gone
    assert services._port_open(port) is False


def test_a_pattern_matching_only_ourselves_is_not_a_running_service():
    """The false positive that made a dead service look alive.

    pgrep -f matches whole command lines, so this test's own process —
    which has the pattern in its arguments — counted as a match. Only a
    process whose working directory is the service's counts.
    """
    marker = "zz-not-a-real-service-zz"
    assert services._running_in(marker, "/nonexistent/directory") is False


def test_status_reports_every_defined_service(script):
    rows = services.status()
    assert {r["label"] for r in rows} == {
        "MySQL", "usaccidents backend", "jarheads scheduler"}
    assert all(isinstance(r["up"], bool) for r in rows)
