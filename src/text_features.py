"""Fast, deterministic, multilingual rule-based extractor from `description`.

This is the always-available backbone for description-derived features (instant, full
coverage, transparent). It produces the SAME schema as the Ollama LLM extractor, so the
two are interchangeable: `llm_extract.apply_to_df` uses the cached LLM result when present
and falls back to this for everything else. Keyword lists include English + common
transliterated-Kannada (Kanglish) terms seen in the data.

Allowed under PS2 rules: this only processes text already in the dataset.
"""
from __future__ import annotations
import re

from . import config as C

DEFAULTS = {
    "severity_score": 2,
    "blocking_lanes": False,
    "vehicles_involved": 0,
    "requires_tow": False,
    "incident_subtype": "other",
}

# subtype keyword groups (checked in priority order)
SUBTYPE_KEYWORDS = [
    ("vip_or_procession", ["vip", "procession", "rally", "dharna", "protest", "convoy",
                            "minister", " cm ", "mla", "mp visit", "march"]),
    ("crowd_or_event", ["event", "function", "festival", "mela", "jatre", "jathre",
                         "crowd", "gathering", "public event", "habba", "utsav", "fair"]),
    ("collision", ["accident", "collision", "collided", "hit ", "dashed", "dash",
                   "crash", "overturn", "toppl", "rammed", "head on"]),
    ("tree_or_debris", ["tree", "branch", "debris", "tree fall", "mara", "log on road"]),
    ("waterlogging_or_pothole", ["water log", "waterlog", "water logging", "pothole",
                                 "pot hole", "flood", "gundi", "rain water", "drain over"]),
    ("construction_or_utility", ["construction", "bwssb", "bescom", "nhai", "bbmp work",
                                 "digging", "pipe", "cable", "chamber", "road work",
                                 "joint cut", "barricad", "metro work", "under construction",
                                 "work in progress", "wip", "utility"]),
    ("vehicle_breakdown", ["breakdown", "break down", "break-down", "broke down", "broken",
                           "puncture", "tyre", "tire", "axle", "axel", "engine", "gearbox",
                           "starting problem", "start problem", "stall", "off aag",
                           "vehicle off", "dead", "fuel", "clutch", "diesel", "battery"]),
    ("congestion_only", ["slow", "jam", "congest", "heavy traffic", "movement", "moment",
                         "normal", "smooth", "peak", "rush"]),
]

BLOCK_TERMS = ["block", "blocked", "closed", "close", "full block", "diversion", "divert",
               "stuck", "cannot pass", "cant pass", "single lane", "one lane", "no movement",
               "road closed", "stopped", "halt", "obstruct", "barricad"]
TOW_TERMS = ["tow", "towing", "crane", "recovery", "lifting", "lift", "shift the veh",
             "shifted", "hydra", "pulled"]
CLEAR_TERMS = ["cleared", "clear", "normal", "no issue", "no problem", "resolved",
               "smooth", "free flow"]
SEVERE_TERMS = ["road closed", "full block", "fully block", "overturn", "major", "severe",
                "huge", "big jam", "completely", "total block", "accident"]
VEHICLE_TERMS = ["vehicle", "lorry", "truck", "bus", "car", "auto", "tempo", "lcv",
                 "container", "tanker", "van", "bike", "two wheeler", "scooter", "cab",
                 "taxi", "veh "]


def _has(text: str, terms) -> bool:
    return any(t in text for t in terms)


def rule_extract(desc: str) -> dict:
    if not desc or not str(desc).strip():
        return dict(DEFAULTS)
    t = " " + str(desc).lower().strip() + " "
    out = dict(DEFAULTS)

    # subtype (first matching group wins)
    for name, kws in SUBTYPE_KEYWORDS:
        if _has(t, kws):
            out["incident_subtype"] = name
            break

    out["blocking_lanes"] = _has(t, BLOCK_TERMS)
    out["requires_tow"] = _has(t, TOW_TERMS)

    # vehicles involved
    nums = re.findall(r"\b(\d{1,2})\b", t)
    if out["incident_subtype"] == "collision":
        out["vehicles_involved"] = 2
    elif _has(t, VEHICLE_TERMS) or out["incident_subtype"] == "vehicle_breakdown":
        out["vehicles_involved"] = 1
    if nums:
        cand = max(int(n) for n in nums if int(n) <= 10) if any(int(n) <= 10 for n in nums) else 0
        out["vehicles_involved"] = max(out["vehicles_involved"], cand)

    # severity heuristic
    sev = 2
    if out["incident_subtype"] in ("congestion_only",):
        sev = 1
    if _has(t, CLEAR_TERMS):
        sev = 1
    if out["blocking_lanes"]:
        sev = 4
    if _has(t, SEVERE_TERMS):
        sev = 5
    if out["incident_subtype"] in ("vip_or_procession", "crowd_or_event") and sev < 3:
        sev = 3
    out["severity_score"] = sev
    return out
