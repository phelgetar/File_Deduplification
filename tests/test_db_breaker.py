#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: test_db_breaker.py
# Purpose: The database circuit breaker
#
# Description:
# A 59-minute run over 37,658 files finished its pipeline and then
# refused --execute, saying the connection had been lost. MySQL had
# not restarted, had not hit its connection limit, and was reachable
# the whole time. Nothing recorded what actually failed, and the
# breaker had latched for the life of the process.
#
# These cover the three fixes: remember the reasons, retry after a
# cooldown, and stop asserting a cause nobody checked.
#
# Author: Tim Canady
# Created: 2026-10-03
#
# Version: 1.0.0
# Last Modified: 2026-10-03 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-10-03): Initial breaker tests — Tim Canady
###################################################################

import time

import pytest

import core.db as db


@pytest.fixture(autouse=True)
def fresh_breaker(monkeypatch):
    """Every test starts with the breaker closed and no history."""
    monkeypatch.setattr(db, "_breaker",
                        {"failures": 0, "down": False, "opened_at": 0.0})
    monkeypatch.setattr(db, "_failure_log", db.deque(maxlen=20))
    monkeypatch.setattr(db, "DB_RETRY_AFTER_SECONDS", 0.2)
    yield


def _always_fails(exc=RuntimeError("boom")):
    @db._db_guard(default="NOOP")
    def op():
        raise exc
    return op


def test_it_takes_three_consecutive_failures():
    op = _always_fails()
    op(); op()
    assert db.is_db_down() is False, "two failures must not trip it"
    op()
    assert db.is_db_down() is True


def test_a_success_resets_the_count():
    state = {"fail": True}

    @db._db_guard(default="NOOP")
    def op():
        if state["fail"]:
            raise RuntimeError("boom")
        return "OK"

    op(); op()
    state["fail"] = False
    assert op() == "OK"
    state["fail"] = True
    op(); op()
    assert db.is_db_down() is False, "the counter must have restarted"


def test_the_reasons_are_recorded():
    """They used to be logger.warning calls that scrolled past, leaving
    the user with a refusal and no way to find out why."""
    @db._db_guard(default=None)
    def save_classification():
        raise ConnectionError("(2013, 'Lost connection during query')")

    for _ in range(3):
        save_classification()

    reasons = db.describe_db_failures()
    assert len(reasons) == 1, "identical failures collapse to one line"
    assert "save_classification" in reasons[0]
    assert "2013" in reasons[0]
    assert len(db.db_failures()) == 3


def test_distinct_failures_are_reported_separately():
    @db._db_guard(default=None)
    def alpha():
        raise RuntimeError("first problem")

    @db._db_guard(default=None)
    def beta():
        raise ValueError("second problem")

    alpha(); beta(); alpha()
    reasons = db.describe_db_failures()
    assert len(reasons) == 2
    assert any("alpha" in r for r in reasons) and any("beta" in r for r in reasons)


def test_calls_are_no_ops_while_it_is_open():
    calls = {"n": 0}

    @db._db_guard(default="NOOP")
    def op():
        calls["n"] += 1
        raise RuntimeError("boom")

    for _ in range(3):
        op()
    assert calls["n"] == 3
    assert op() == "NOOP"
    assert calls["n"] == 3, "the database must not be touched while open"


def test_it_retries_after_the_cooldown_and_recovers():
    """The expensive part of the old behaviour. A blip in minute 3 of a
    59-minute run disabled persistence for the remaining 56 and refused
    --execute at the end."""
    state = {"fail": True}

    @db._db_guard(default="NOOP")
    def op():
        if state["fail"]:
            raise RuntimeError("boom")
        return "OK"

    for _ in range(3):
        op()
    assert db.is_db_down() is True

    time.sleep(db.DB_RETRY_AFTER_SECONDS + 0.05)
    assert db.is_db_down() is False, "the cooldown lets one call through"

    state["fail"] = False
    assert op() == "OK"
    assert db.is_db_down() is False, "a success closes it"
    assert db._breaker["failures"] == 0


def test_a_failed_probe_leaves_it_open():
    op = _always_fails()
    for _ in range(3):
        op()
    time.sleep(db.DB_RETRY_AFTER_SECONDS + 0.05)
    op()                                   # the probe fails
    assert db.is_db_down() is True


def test_the_engine_replaces_stale_connections():
    """pool_pre_ping is why a dropped idle connection is no longer a
    query failure, and so no longer counts toward the breaker."""
    assert db.engine.pool._pre_ping is True
    assert db.engine.pool._recycle == 1800
