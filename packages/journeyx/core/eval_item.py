from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EvalCategory = Literal[
    "refusal",
    "clarify",
    "rag_qa",
    "transport_compare",
    "full_plan",
    "refine",
]


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class EvalItem(BaseModel):
    id: str
    query: str
    category: EvalCategory
    gold_facts: list[str]
    reference_answer_short: str | None = None
    gold_rubric: list[str] = Field(default_factory=list)
    expected_tools: list[str] = Field(default_factory=list)
    must_not: list[str] = Field(default_factory=list)
    expected_refusal: bool = False
    refusal_rationale: str | None = None
    relevant_doc_ids: list[str] = Field(default_factory=list)
    conversation_prefix: list[ConversationTurn] = Field(default_factory=list)
    corpus_version: str = "v1"
    hold_out_destination: bool = False