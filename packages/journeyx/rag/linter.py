from __future__ import annotations

import re
from dataclasses import dataclass

from journeyx.core.structured import TravelDocument

CURRENCY_PATTERN = re.compile(r"(?:₹|rs\.?|inr)\s*[\d,]+", re.I)
STANDALONE_PRICE = re.compile(r"\b\d{3,6}\s*(?:per night|/night|inr)\b", re.I)


@dataclass
class LintIssue:
    doc_id: str
    severity: str
    message: str


def lint_documents(documents: list[TravelDocument]) -> list[LintIssue]:
    issues: list[LintIssue] = []
    for doc in documents:
        if doc.doc_type in ("accommodation_blurb",):
            continue
        body = doc.body
        if CURRENCY_PATTERN.search(body) and not doc.linked_poi_id and not doc.linked_stay_id:
            issues.append(
                LintIssue(
                    doc_id=doc.doc_id,
                    severity="warning",
                    message="Currency literal without linked_poi_id/stay_id (SoT rule)",
                )
            )
        if STANDALONE_PRICE.search(body) and doc.doc_type not in ("transport_guide",):
            if not doc.linked_stay_id:
                issues.append(
                    LintIssue(
                        doc_id=doc.doc_id,
                        severity="info",
                        message="Possible standalone price in narrative",
                    )
                )
    return issues