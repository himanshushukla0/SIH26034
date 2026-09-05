"""
SIH26034 — LangGraph Multi-Agent Orchestrator

Wires all agents (Scraper → Vision → LMPC Evaluator → Report Generator)
into a stateful LangGraph pipeline with conditional routing based on
input type (image upload vs. e-commerce URL).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Literal, Optional

from langgraph.graph import StateGraph, END

from backend.agents.vision_agent import vision_agent
from backend.agents.scraper_agent import scraper_agent
from backend.agents.lmpc_evaluator import lmpc_evaluator, AuditVerdict
from backend.agents.verification_agent import verification_agent, PackageAuthenticityVerdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline State
# ---------------------------------------------------------------------------

@dataclass
class AuditState:
    """Shared state flowing through the LangGraph pipeline."""

    # --- Inputs ---
    input_type: str = ""                    # "image" or "url"
    image_bytes: Optional[bytes] = None
    image_path: Optional[str] = None
    source_url: Optional[str] = None

    # --- Scraper Output ---
    platform: str = ""
    listing_data: dict[str, Any] = field(default_factory=dict)
    downloaded_images: list[str] = field(default_factory=list)

    # --- Vision Output ---
    extractions: dict[str, Any] = field(default_factory=dict)

    # --- Evaluator Output ---
    verdict: Optional[dict[str, Any]] = None

    # --- Verification Output ---
    verification: Optional[dict[str, Any]] = None

    # --- Error Tracking ---
    error: Optional[str] = None
    stage: str = "initialized"


# ---------------------------------------------------------------------------
# Pipeline Nodes
# ---------------------------------------------------------------------------

async def scrape_node(state: AuditState) -> AuditState:
    """Node 1: Scrape e-commerce listing (only for URL inputs)."""
    state.stage = "scraping"
    logger.info("🛒 Scraper Agent: Crawling %s", state.source_url)

    try:
        result = await scraper_agent.scrape_product(state.source_url)
        state.platform = result["platform"]
        state.listing_data = result["listing_data"]
        state.downloaded_images = result["downloaded_images"]
        state.stage = "scraped"
    except Exception as e:
        state.error = f"Scraping failed: {e}"
        state.stage = "error"
        logger.error("Scraper Agent error: %s", e)

    return state


async def vision_node(state: AuditState) -> AuditState:
    """Node 2: Extract declarations from packaging image via Gemini Vision."""
    state.stage = "extracting"
    logger.info("👁️ Vision Agent: Extracting declarations from image")

    try:
        # Determine image source
        if state.image_bytes:
            extractions = await vision_agent.extract_from_image(
                image_bytes=state.image_bytes
            )
        elif state.image_path:
            extractions = await vision_agent.extract_from_image(
                image_path=state.image_path
            )
        elif state.downloaded_images:
            # Use first scraped image (typically front-of-pack)
            extractions = await vision_agent.extract_from_image(
                image_path=state.downloaded_images[0]
            )
        else:
            state.error = "No image available for vision processing."
            state.stage = "error"
            return state

        state.extractions = extractions
        state.stage = "extracted"

    except Exception as e:
        state.error = f"Vision extraction failed: {e}"
        state.stage = "error"
        logger.error("Vision Agent error: %s", e)

    return state


async def evaluator_node(state: AuditState) -> AuditState:
    """Node 3: Run LMPC compliance checks on extracted declarations."""
    state.stage = "evaluating"
    logger.info("🏛️ LMPC Evaluator: Running compliance checks")

    try:
        verdict: AuditVerdict = lmpc_evaluator.evaluate(
            extractions=state.extractions,
            listing_data=state.listing_data if state.listing_data else None,
        )

        # Convert verdict to serializable dict
        state.verdict = {
            "compliance_score": verdict.compliance_score,
            "total_checks": verdict.total_checks,
            "passed_checks": verdict.passed_checks,
            "failed_checks": verdict.failed_checks,
            "overall_status": verdict.overall_status,
            "computed_usp": verdict.computed_usp,
            "declaration_status": verdict.declaration_status,
            "violations": [
                {
                    "rule_reference": v.rule_reference,
                    "field_name": v.field_name,
                    "severity": v.severity,
                    "description": v.description,
                    "expected_value": v.expected_value,
                    "found_value": v.found_value,
                    "is_discrepancy": v.is_discrepancy,
                }
                for v in verdict.violations
            ],
        }
        state.stage = "evaluated"

    except Exception as e:
        state.error = f"LMPC evaluation failed: {e}"
        state.stage = "error"
        logger.error("LMPC Evaluator error: %s", e)

    return state


async def verify_node(state: AuditState) -> AuditState:
    """Node 4: Cross-verify extracted declarations against external databases."""
    state.stage = "verifying"
    logger.info("🛡️ Verification Agent: Cross-verifying against external databases")

    try:
        auth_verdict: PackageAuthenticityVerdict = await verification_agent.verify(
            extractions=state.extractions,
            listing_data=state.listing_data if state.listing_data else None,
        )

        state.verification = {
            "trust_score": auth_verdict.trust_score,
            "overall_status": auth_verdict.overall_status,
            "counterfeit_signals": auth_verdict.counterfeit_signals,
            "expiry_status": auth_verdict.expiry_status,
            "days_until_expiry": auth_verdict.days_until_expiry,
            "checks": [
                {
                    "check_name": c.check_name,
                    "status": c.status,
                    "confidence": c.confidence,
                    "details": c.details,
                    "evidence": c.evidence,
                    "is_counterfeit_signal": c.is_counterfeit_signal,
                }
                for c in auth_verdict.checks
            ],
        }
        state.stage = "completed"

    except Exception as e:
        state.error = f"Verification failed: {e}"
        state.stage = "error"
        logger.error("Verification Agent error: %s", e)

    return state


# ---------------------------------------------------------------------------
# Routing Logic
# ---------------------------------------------------------------------------

def route_input(state: AuditState) -> str:
    """Determine which node to start with based on input type."""
    if state.error:
        return "end"
    if state.input_type == "url":
        return "scrape"
    return "vision"


def route_after_scrape(state: AuditState) -> str:
    """After scraping, proceed to vision processing."""
    if state.error:
        return "end"
    return "vision"


def route_after_vision(state: AuditState) -> str:
    """After vision extraction, proceed to compliance evaluation."""
    if state.error:
        return "end"
    return "evaluate"


def route_after_evaluate(state: AuditState) -> str:
    """After evaluation, proceed to verification."""
    if state.error:
        return "end"
    return "verify"


def route_after_verify(state: AuditState) -> str:
    """After verification, pipeline is complete."""
    return "end"


# ---------------------------------------------------------------------------
# Build the LangGraph Pipeline
# ---------------------------------------------------------------------------

def build_audit_pipeline() -> StateGraph:
    """
    Construct the multi-agent LangGraph pipeline.

    Flow:
        [URL Input] → Scraper → Vision → Evaluator → Verifier → END
        [Image Input] → Vision → Evaluator → Verifier → END
    """
    workflow = StateGraph(AuditState)

    # Add nodes
    workflow.add_node("scrape", scrape_node)
    workflow.add_node("vision", vision_node)
    workflow.add_node("evaluate", evaluator_node)
    workflow.add_node("verify", verify_node)

    # Set entry point with conditional routing
    workflow.set_conditional_entry_point(
        route_input,
        {
            "scrape": "scrape",
            "vision": "vision",
            "end": END,
        },
    )

    # Add edges with conditional routing
    workflow.add_conditional_edges(
        "scrape",
        route_after_scrape,
        {"vision": "vision", "end": END},
    )
    workflow.add_conditional_edges(
        "vision",
        route_after_vision,
        {"evaluate": "evaluate", "end": END},
    )
    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"verify": "verify", "end": END},
    )
    workflow.add_conditional_edges(
        "verify",
        route_after_verify,
        {"end": END},
    )

    return workflow.compile()


# Module-level compiled pipeline
audit_pipeline = build_audit_pipeline()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_image_audit(
    image_bytes: Optional[bytes] = None,
    image_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Run a full LMPC compliance audit on a packaging image.

    Args:
        image_bytes: Raw image bytes from upload.
        image_path: Path to image file on disk.

    Returns:
        Complete audit result dictionary.
    """
    initial_state = AuditState(
        input_type="image",
        image_bytes=image_bytes,
        image_path=image_path,
    )

    final_state = await audit_pipeline.ainvoke(initial_state)

    return {
        "input_type": "image",
        "stage": final_state.stage,
        "error": final_state.error,
        "extractions": final_state.extractions,
        "verdict": final_state.verdict,
        "verification": final_state.verification,
    }


async def run_url_audit(url: str) -> dict[str, Any]:
    """
    Run a full LMPC compliance audit on an e-commerce product listing.

    Args:
        url: Product page URL (Amazon, Flipkart, Blinkit, etc.)

    Returns:
        Complete audit result with cross-modal discrepancy checks.
    """
    initial_state = AuditState(
        input_type="url",
        source_url=url,
    )

    final_state = await audit_pipeline.ainvoke(initial_state)

    return {
        "input_type": "url",
        "source_url": url,
        "platform": final_state.platform,
        "stage": final_state.stage,
        "error": final_state.error,
        "listing_data": final_state.listing_data,
        "extractions": final_state.extractions,
        "verdict": final_state.verdict,
        "verification": final_state.verification,
    }
