"""Result categories, labels and colours shared by the reports and the web app."""

from __future__ import annotations


class Status:
    CORRECT = "CORRECT"
    WRONG_SIDE = "WRONG_SIDE"
    OUT_OF_PLACE = "OUT_OF_PLACE"
    UNKNOWN_NUMBER = "UNKNOWN_NUMBER"
    SUFFIX_MISMATCH = "SUFFIX_MISMATCH"
    NO_ADDRESS_NEARBY = "NO_ADDRESS_NEARBY"
    UNREADABLE = "UNREADABLE"
    UNCERTAIN = "UNCERTAIN"
    NOT_FOUND = "NOT_FOUND"
    NOT_COVERED = "NOT_COVERED"
    IN_VIEW = "IN_VIEW"


STATUS_INFO: dict[str, dict] = {
    Status.CORRECT: {
        "label": "Correct",
        "color": "#1a7f37",
        "problem": False,
        "meaning": "The plate shows the official number at this location.",
    },
    Status.WRONG_SIDE: {
        "label": "Wrong side",
        "color": "#cf222e",
        "problem": True,
        "meaning": "The number exists on this street, but on the opposite side.",
    },
    Status.OUT_OF_PLACE: {
        "label": "Out of place",
        "color": "#be185d",
        "problem": True,
        "meaning": "The number exists, but its official position is somewhere else.",
    },
    Status.UNKNOWN_NUMBER: {
        "label": "Unknown number",
        "color": "#7f1d1d",
        "problem": True,
        "meaning": "The number is not in the official list for this street.",
    },
    Status.SUFFIX_MISMATCH: {
        "label": "Suffix mismatch",
        "color": "#c2410c",
        "problem": True,
        "meaning": "Same number, but the suffix (bis, ter, letter) differs from the official one.",
    },
    Status.NO_ADDRESS_NEARBY: {
        "label": "No address here",
        "color": "#7c3aed",
        "problem": True,
        "meaning": "No official address at the plate location and the number is not on a nearby street.",
    },
    Status.UNREADABLE: {
        "label": "Unreadable",
        "color": "#475569",
        "problem": False,
        "meaning": "A plate is present but its number cannot be read.",
    },
    Status.UNCERTAIN: {
        "label": "Uncertain",
        "color": "#9ca3af",
        "problem": False,
        "meaning": "The evidence is not strong enough for a decision. A person should review it.",
    },
    Status.NOT_FOUND: {
        "label": "Plate not found",
        "color": "#d97706",
        "problem": True,
        "meaning": "The address was in view in several photos, but no plate was found.",
    },
    Status.NOT_COVERED: {
        "label": "Not enough views",
        "color": "#cbd5e1",
        "problem": False,
        "meaning": "The address was in view in too few photos to be judged.",
    },
    Status.IN_VIEW: {
        "label": "In view",
        "color": "#2563eb",
        "problem": False,
        "meaning": "Inspection mode: the address should be visible in the listed photos.",
    },
}


def label(status: str) -> str:
    return STATUS_INFO.get(status, {}).get("label", status)


def color(status: str) -> str:
    return STATUS_INFO.get(status, {}).get("color", "#6b7280")


def is_problem(status: str) -> bool:
    return bool(STATUS_INFO.get(status, {}).get("problem", False))
