#!/usr/bin/env python3
#
###################################################################
# Project: File_Deduplification
# File: engine.py
# Purpose: The classification escalation ladder
#
# Description:
# Three tiers, cheapest first, each handling only what the one below
# it could not:
#
#   1. rules   core/classifier.py    free, ~instant, handles the bulk
#   2. local   core/llm_client.py    free, Ollama, handles most of the rest
#   3. cloud   classify/cloud.py     costs money, capped, last resort
#
# The point of the ordering is that tier 3 only ever sees files two
# earlier passes already failed on — typically a fraction of a percent
# of a run — so the spend stays small and bounded even on a large tree.
#
# Tiers 1 and 2 are driven directly by core/pipeline.py (they are stages
# with different parallelism needs). This module owns the policy that
# decides what escalates, and runs tier 3.
#
# Author: Tim Canady
# Created: 2026-08-17
#
# Version: 0.1.0
# Last Modified: 2026-08-17 by Tim Canady
#
# Revision History:
# - 0.1.0 (2026-08-17): Initial ladder policy and cloud tier runner — Tim Canady
###################################################################

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

from core import parallel

logger = logging.getLogger(__name__)


@dataclass
class LadderConfig:
    """Which tiers to run, and what the cloud tier is allowed to spend."""

    use_local: bool = False
    use_cloud: bool = False

    # Hard ceiling for one run. Enforced against actual token usage, not
    # against the pre-flight estimate.
    cloud_cost_limit_usd: float = 1.00
    cloud_model: Optional[str] = None

    # A local answer at or below this confidence is treated as unresolved
    # and escalated. 0.0 escalates only files still labelled "other".
    escalate_below_confidence: float = 0.5


def escalation_candidates(classified, threshold: float = 0.5) -> List:
    """Files the cheaper tiers failed to place.

    A file qualifies when it is still 'other' — the rules' and the local
    model's way of saying "no idea". Confidence is consulted when the
    pipeline recorded one.
    """
    out = []
    for f in classified:
        if f.type in (None, "", "other"):
            out.append(f)
            continue
        confidence = getattr(f, "confidence", None)
        if confidence is not None and confidence < threshold:
            out.append(f)
    return out


def preflight(candidates, config: LadderConfig) -> dict:
    """Price the cloud tier before running it.

    Returned to the UI so the user sees a number, and compared against
    the configured cap so an over-budget batch is caught before the
    first request rather than partway through.
    """
    from classify import cloud

    estimate = cloud.estimate_cost((f.path for f in candidates), config.cloud_model)
    estimate["cost_limit_usd"] = config.cloud_cost_limit_usd
    estimate["within_budget"] = estimate["estimated_cost_usd"] <= config.cloud_cost_limit_usd
    return estimate


def run_cloud_tier(
    candidates,
    config: LadderConfig,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> dict:
    """Classify the leftovers with Claude, stopping at the spend cap.

    Mutates each FileInfo's `type` in place on success, so the caller can
    persist them exactly as it persists the other tiers' results.

    Runs on the LLM policy (a small thread pool) rather than the CPU
    policy: this stage waits on a remote API, and the useful limit is
    request concurrency, not core count.
    """
    from classify.cloud import CloudClassifier, is_available

    summary = {"attempted": 0, "resolved": 0, "failed": 0,
               "spent_usd": 0.0, "capped": False}

    if not candidates:
        return summary
    if not is_available():
        logger.warning("Cloud tier unavailable: install `anthropic` and set "
                       "ANTHROPIC_API_KEY (or run `ant auth login`).")
        return summary

    classifier = CloudClassifier(model=config.cloud_model,
                                 cost_limit_usd=config.cloud_cost_limit_usd)
    by_path = {str(f.path): f for f in candidates}

    def stop() -> bool:
        # Two independent stop conditions: the user cancelled, or the
        # run hit its ceiling. Either ends the stage cleanly with the
        # already-classified files kept.
        if cancel is not None and cancel():
            return True
        if classifier.cap.exceeded():
            summary["capped"] = True
            return True
        return False

    def classify_one(file_info):
        return classifier.classify(file_info.path)

    for result in parallel.map_stage(
        parallel.LLM, classify_one, list(candidates),
        progress=progress, cancel=stop,
    ):
        summary["attempted"] += 1
        if result.category:
            summary["resolved"] += 1
            target = by_path.get(result.path)
            if target is not None:
                target.type = result.category
        else:
            summary["failed"] += 1

    summary["spent_usd"] = round(classifier.cap.spent, 4)
    if summary["capped"]:
        logger.warning("Cloud tier stopped at the $%.2f cap after %d files",
                       config.cloud_cost_limit_usd, summary["attempted"])
    return summary
