#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: test_image_nan.py
# Purpose: Non-finite EXIF values must never reach MySQL
#
# Description:
# A Stealth Cam PX-Series writes GPS tags it never populated, as the
# rational 0/0. That evaluates to NaN, MySQL rejects NaN outright
# ("nan can not be used with MySQL"), and the whole INSERT failed, so
# every photo from that camera got no metadata row at all over a
# coordinate it did not have.
#
# Author: Tim Canady
# Created: 2026-10-04
#
# Version: 1.0.0
# Last Modified: 2026-10-04 by Tim Canady
#
# Revision History:
# - 1.0.0 (2026-10-04): Initial non-finite EXIF tests — Tim Canady
###################################################################

import math
from types import SimpleNamespace

import pytest

from core.image_analyzer import ImageAnalyzer
from core.image_db import _scrub_non_finite


@pytest.fixture
def analyzer():
    return ImageAnalyzer()


def test_a_zero_over_zero_coordinate_becomes_none(analyzer):
    """0/0 is how a camera says "I have no fix", not a location."""
    nan = float("nan")
    assert analyzer._convert_to_degrees([nan, nan, nan], "N") is None


def test_an_infinite_coordinate_becomes_none(analyzer):
    inf = float("inf")
    assert analyzer._convert_to_degrees([inf, 0, 0], "N") is None


def test_a_real_coordinate_still_converts(analyzer):
    """39 degrees 46 minutes 30 seconds north."""
    got = analyzer._convert_to_degrees([39, 46, 30], "N")
    assert got == pytest.approx(39.775, abs=1e-6)


def test_south_and_west_stay_negative(analyzer):
    assert analyzer._convert_to_degrees([39, 46, 30], "S") == pytest.approx(-39.775)
    assert analyzer._convert_to_degrees([84, 3, 0], "W") == pytest.approx(-84.05)


def test_the_scrub_catches_every_non_finite_float():
    """Defence in depth. GPS was the field that bit, but any EXIF
    rational with a zero denominator arrives the same way."""
    md = SimpleNamespace(
        gps_latitude=float("nan"), gps_longitude=float("-inf"),
        f_number=float("inf"), focal_length=7.3,
        width=3840, camera_make="Stealth Cam", date_taken=None,
    )
    dropped = _scrub_non_finite(md)
    assert set(dropped) == {"gps_latitude", "gps_longitude", "f_number"}
    assert md.gps_latitude is None and md.gps_longitude is None
    assert md.f_number is None
    assert md.focal_length == 7.3, "finite values are untouched"
    assert md.width == 3840 and md.camera_make == "Stealth Cam"


def test_the_scrub_reports_nothing_when_all_is_well():
    md = SimpleNamespace(f_number=3.0, focal_length=7.3, width=100)
    assert _scrub_non_finite(md) == []


def test_zero_is_not_confused_with_missing():
    """0.0 is finite and a legitimate value, for example exposure bias."""
    md = SimpleNamespace(exposure_bias=0.0, gps_altitude=0.0)
    assert _scrub_non_finite(md) == []
    assert md.exposure_bias == 0.0 and md.gps_altitude == 0.0
