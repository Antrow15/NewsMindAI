"""Fact checks — block invented numbers/currency relative to source."""

from __future__ import annotations

import re


def _tokens(pattern: str, text: str) -> set[str]:
    return set(re.findall(pattern, text or "", re.I))


def validate_facts(source: str, output: str) -> dict:
    source_numbers = _tokens(r"\b\d[\d,.]*\b", source)
    output_numbers = _tokens(r"\b\d[\d,.]*\b", output)
    invented = sorted(output_numbers - source_numbers)

    source_currency = _tokens(r"(?:₹|\$|£|€)\s*\d[\d,.]*", source)
    output_currency = _tokens(r"(?:₹|\$|£|€)\s*\d[\d,.]*", output)
    invented_currency = sorted(output_currency - source_currency)

    return {
        "invented_numbers": invented,
        "invented_currency": invented_currency,
        "passed": not invented and not invented_currency,
    }
