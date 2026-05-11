"""Node skeletons for the LangGraph workflow.

Each function should be small, testable, and return a partial state update. Avoid mutating the
input state in place.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from .state import AgentState, ApprovalDecision, Route, make_event

RISKY_KEYWORDS = {"refund", "delete", "send", "cancel", "remove", "revoke"}
TOOL_KEYWORDS = {"status", "order", "lookup", "check", "track", "find", "search"}
ERROR_KEYWORDS = {"timeout", "fail", "failure", "error", "crash", "unavailable"}
VAGUE_PRONOUNS = {"it", "this", "that", "they", "them"}
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}\b")
CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
WHITESPACE_RE = re.compile(r"\s+")


def _tokenize(query: str) -> list[str]:
    return re.findall(r"\b[\w']+\b", query.lower())


def _normalize_query(query: str) -> str:
    return WHITESPACE_RE.sub(" ", query.strip())


def _detect_pii(query: str) -> list[str]:
    findings: list[str] = []
    if EMAIL_RE.search(query):
        findings.append("email")
    if PHONE_RE.search(query):
        findings.append("phone")
    if CARD_RE.search(query):
        findings.append("payment_card")
    return findings


def _redact_query(query: str) -> str:
    redacted = EMAIL_RE.sub("[email]", query)
    redacted = PHONE_RE.sub("[phone]", redacted)
    redacted = CARD_RE.sub("[card]", redacted)
    return redacted


def _metadata(query: str, pii_findings: Iterable[str]) -> dict[str, object]:
    tokens = _tokenize(query)
    return {
        "char_count": len(query),
        "word_count": len(tokens),
        "token_count": len(tokens),
        "contains_digits": any(ch.isdigit() for ch in query),
        "contains_pii": bool(list(pii_findings)),
        "pii_types": list(pii_findings),
    }


def _make_structured_tool_output(
    scenario_id: str,
    attempt: int,
    status: str,
    detail: str,
    idempotency_key: str,
    tool_variant: str | None,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "attempt": attempt,
        "status": status,
        "detail": detail,
        "idempotency_key": idempotency_key,
        "tool_variant": tool_variant,
    }


def intake_node(state: AgentState) -> dict:
    """Normalize raw query into state fields."""
    query = _normalize_query(state.get("query", ""))
    pii_findings = _detect_pii(query)
    metadata = _metadata(query, pii_findings)
    redacted = _redact_query(query)
    return {
        "query": query,
        "normalized_query": redacted,
        "extracted_metadata": metadata,
        "pii_findings": list(pii_findings),
        "messages": [f"intake:{query[:40]}"],
        "events": [
            make_event(
                "intake",
                "completed",
                "query normalized",
                pii_detected=bool(pii_findings),
                pii_types=list(pii_findings),
                metadata=metadata,
            )
        ],
    }


def classify_node(state: AgentState) -> dict:
    """Classify the query into a route.
    Required routes: simple, tool, missing_info, risky, error.
    """
    query = state.get("query", "")
    words = _tokenize(query)
    word_set = set(words)
    route = Route.SIMPLE
    risk_level = "low"
    if word_set & RISKY_KEYWORDS:
        route = Route.RISKY
        risk_level = "high"
    elif word_set & TOOL_KEYWORDS:
        route = Route.TOOL
    elif len(words) < 5 and word_set & VAGUE_PRONOUNS:
        route = Route.MISSING_INFO
    elif word_set & ERROR_KEYWORDS:
        route = Route.ERROR
    return {
        "route": route.value,
        "risk_level": risk_level,
        "events": [make_event("classify", "completed", f"route={route.value}")],
    }


def ask_clarification_node(state: AgentState) -> dict:
    """Ask for missing information instead of hallucinating."""
    query = state.get("query", "").lower()
    if "order" in query:
        question = "What is the order id?"
    elif "customer" in query:
        question = "Which customer or account should I use?"
    elif "it" in _tokenize(query):
        question = "What does 'it' refer to?"
    else:
        question = "Can you share the missing details needed to continue?"
    return {
        "pending_question": question,
        "final_answer": question,
        "events": [
            make_event("clarify", "completed", "missing information requested", question=question)
        ],
    }


def tool_node(state: AgentState) -> dict:
    """Call a mock tool.
    Simulates transient failures for error-route scenarios to demonstrate retry loops.
    """
    attempt = int(state.get("attempt", 0))
    should_retry = bool(state.get("should_retry"))
    route = state.get("route")
    scenario_id = str(state.get("scenario_id", "unknown"))
    tool_variant = state.get("tool_variant") or "single"
    idempotency_key = f"{scenario_id}:{route}:{tool_variant}:{attempt}"
    should_fail = (should_retry or route == Route.ERROR.value) and attempt < 1
    if should_fail:
        detail = f"transient failure attempt={attempt} scenario={scenario_id}"
        structured = _make_structured_tool_output(
            scenario_id, attempt, "error", detail, idempotency_key, tool_variant
        )
    else:
        detail = f"mock-tool-result for scenario={scenario_id} variant={tool_variant}"
        structured = _make_structured_tool_output(
            scenario_id, attempt, "ok", detail, idempotency_key, tool_variant
        )
    return {
        "tool_outputs": [structured],
        "tool_results": [json.dumps(structured, ensure_ascii=False)],
        "events": [
            make_event(
                "tool",
                "completed",
                f"tool executed attempt={attempt}",
                status=structured["status"],
                idempotency_key=idempotency_key,
                tool_variant=tool_variant,
            )
        ],
    }


def tool_primary_node(state: AgentState) -> dict:
    """Parallel tool branch one."""
    return tool_node({**state, "tool_variant": "primary"})


def tool_secondary_node(state: AgentState) -> dict:
    """Parallel tool branch two."""
    return tool_node({**state, "tool_variant": "secondary"})


def risky_action_node(state: AgentState) -> dict:
    """Prepare a risky action for approval."""
    query = state.get("query", "")
    proposed = f"Review external action for: {query}"
    details = {
        "action": "external_side_effect",
        "risk_level": state.get("risk_level", "unknown"),
        "evidence": query,
        "justification": "High-risk request needs human approval before any side effect",
    }
    return {
        "proposed_action": proposed,
        "proposed_action_details": details,
        "events": [make_event("risky_action", "pending_approval", "approval required", **details)],
    }


def approval_node(state: AgentState) -> dict:
    """Human approval step with optional LangGraph interrupt().

    Set LANGGRAPH_INTERRUPT=true to use real interrupt() for HITL demos.
    Default uses mock decision so tests and CI run offline.
    """
    import os

    if os.getenv("LANGGRAPH_INTERRUPT", "").lower() == "true":
        from langgraph.types import interrupt

        try:
            value = interrupt(
                {
                    "proposed_action": state.get("proposed_action"),
                    "risk_level": state.get("risk_level"),
                    "proposal": state.get("proposed_action_details"),
                }
            )
        except TimeoutError:
            decision = ApprovalDecision(approved=False, comment="approval timed out")
            timeout = True
            edited_action = None
        else:
            timeout = False
            edited_action = None
            if isinstance(value, dict):
                edited_action = value.get("edited_action")
                approved = bool(value.get("approved", False))
                if edited_action:
                    approved = True
                decision = ApprovalDecision(
                    approved=approved,
                    reviewer=str(value.get("reviewer", "human-reviewer")),
                    comment=str(value.get("comment", "")),
                )
            else:
                decision = ApprovalDecision(approved=bool(value))
    else:
        decision = ApprovalDecision(approved=True, comment="mock approval for lab")
        timeout = False
        edited_action = None

    proposed_action = state.get("proposed_action")
    if edited_action:
        proposed_action = str(edited_action)
    return {
        "proposed_action": proposed_action,
        "approval_timed_out": timeout,
        "approval": decision.model_dump(),
        "events": [
            make_event(
                "approval",
                "completed",
                f"approved={decision.approved}",
                timed_out=timeout,
                edited=bool(edited_action),
            )
        ],
    }


def retry_or_fallback_node(state: AgentState) -> dict:
    """Record a retry attempt or fallback decision."""
    attempt = int(state.get("attempt", 0)) + 1
    max_attempts = int(state.get("max_attempts", 3))
    backoff_ms = min(100 * (2 ** max(0, attempt - 1)), 5000)
    errors = [f"transient failure attempt={attempt}"]
    if attempt >= max_attempts:
        errors.append("retry budget exhausted")
    return {
        "attempt": attempt,
        "retry_backoff_ms": backoff_ms,
        "errors": errors,
        "events": [
            make_event(
                "retry",
                "completed",
                "retry attempt recorded",
                attempt=attempt,
                backoff_ms=backoff_ms,
                max_attempts=max_attempts,
            )
        ],
    }


def answer_node(state: AgentState) -> dict:
    """Produce a final response."""
    approval = state.get("approval") or {}
    tool_outputs = state.get("tool_outputs") or []
    if tool_outputs:
        ok_outputs = [item for item in tool_outputs if item.get("status") == "ok"]
        if ok_outputs:
            seen: set[str] = set()
            details_list = []
            for item in ok_outputs:
                detail = str(item.get("detail", ""))
                if detail and detail not in seen:
                    seen.add(detail)
                    details_list.append(detail)
            details = "; ".join(details_list)
            answer = details or "Tool completed successfully."
            if approval.get("approved") and state.get("proposed_action"):
                answer = f"{answer} Approved action: {state['proposed_action']}"
        else:
            answer = state.get("final_answer") or "Tool output unavailable."
    elif state.get("pending_question"):
        answer = str(state["pending_question"])
    else:
        answer = "This is a safe mock answer. Replace with your agent response."
    return {
        "final_answer": answer,
        "events": [
            make_event("answer", "completed", "answer generated", used_tool=bool(tool_outputs))
        ],
    }


def evaluate_node(state: AgentState) -> dict:
    """Evaluate tool results — the 'done?' check that enables retry loops."""
    tool_outputs = state.get("tool_outputs", [])
    latest = tool_outputs[-1] if tool_outputs else {}
    if any(item.get("status") == "error" for item in tool_outputs):
        return {
            "evaluation_result": "needs_retry",
            "events": [
                make_event(
                    "evaluate",
                    "completed",
                    "tool result indicates failure, retry needed",
                    status="error",
                    detail=latest.get("detail"),
                )
            ],
    }
    return {
        "evaluation_result": "success",
        "events": [
            make_event(
                "evaluate",
                "completed",
                "tool result satisfactory",
                status="ok",
                outputs=len(tool_outputs),
            )
        ],
    }


def dead_letter_node(state: AgentState) -> dict:
    """Log unresolvable failures for manual review.

    Third layer of error strategy: retry -> fallback -> dead letter.
    """
    attempt = int(state.get("attempt", 0))
    reason = f"max retries exceeded at attempt={attempt}"
    ticket = {
        "ticket_id": f"dlq-{state.get('scenario_id', 'unknown')}",
        "scenario_id": state.get("scenario_id"),
        "attempt": attempt,
        "reason": reason,
        "route": state.get("route", "unknown"),
    }
    return {
        "dead_letter_reason": reason,
        "dead_letter_ticket": ticket,
        "final_answer": (
            "Request could not be completed after maximum retry attempts. "
            "Logged for manual review."
        ),
        "events": [make_event("dead_letter", "completed", reason, ticket=ticket)],
    }


def finalize_node(state: AgentState) -> dict:
    """Finalize the run and emit a final audit event."""
    return {"events": [make_event("finalize", "completed", "workflow finished")]}
