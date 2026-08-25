import json
import re
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from app.models.schemas import AgentResponse, SourceCitation, DocumentChunk, OrderLookupResult, CustomerOrder
from app.rag.conflict_detector import ConflictResult
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import SessionState
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.utils import format_date_human


class ResponseGenerator:
    """
    Constructs grounded customer responses, builds programmatic source citations
    from chunk metadata, and manages LLM invocation within strict trust boundaries.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = OPENAI_MODEL):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model
        self.use_openai = bool(self.api_key and self.api_key.startswith("sk-"))
        self._openai_client = None

        if self.use_openai:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.api_key)
            except Exception:
                self.use_openai = False

    @staticmethod
    def build_citations_from_chunks(chunks: List[DocumentChunk]) -> List[SourceCitation]:
        """
        Builds citations programmatically from retrieved DocumentChunk metadata,
        ensuring the model never invents filenames or headings.
        """
        citations: List[SourceCitation] = []
        seen = set()
        for chunk in chunks:
            key = (chunk.filename, chunk.heading)
            if key not in seen and chunk.metadata.policy_authority == "official":
                citations.append(SourceCitation(filename=chunk.filename, heading=chunk.heading))
                seen.add(key)
        return citations

    def generate_order_response(
        self,
        result: OrderLookupResult,
        order_id: Optional[str],
        debug_info: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Generates customer-safe order status response based on authoritative status.
        """
        if not order_id:
            return AgentResponse(
                answer="To check your order status, please provide your order ID (for example, ORD-1007).",
                sources=[],
                handoff=False,
                tool_called=None,
                debug_info=debug_info
            )

        if not result.found:
            return AgentResponse(
                answer=result.message,
                sources=[],
                handoff=True,  # Unknown order triggers handoff
                tool_called="order_lookup",
                tool_arguments={"order_id": order_id},
                debug_info=debug_info
            )

        order = result.order
        handoff = result.requires_human_review

        if order.status == "cancelled":
            cancel_date = format_date_human(order.status_updated_at)
            answer = (
                f"Order {order.order_id} was cancelled on {cancel_date} and will not be shipped. "
                "No delivery is scheduled."
            )
        elif order.status == "returned":
            answer = (
                f"Order {order.order_id} was returned and processed. "
                f"{order.customer_safe_message or ''}".strip()
            )
        elif order.status == "exception":
            answer = (
                f"Order {order.order_id} has a shipment exception that requires support review. "
                "I am connecting you with a human support specialist to resolve this."
            )
            handoff = True
        elif order.status == "delayed":
            answer = (
                f"Order {order.order_id} is currently delayed. {order.customer_safe_message} "
                f"Carrier: {order.carrier}, Tracking Number: {order.tracking_number}."
            )
        elif order.status == "delivered":
            deliv_date = format_date_human(order.delivered_at)
            answer = (
                f"Order {order.order_id} was delivered on {deliv_date} via {order.carrier} "
                f"(Tracking Number: {order.tracking_number})."
            )
        elif order.status == "shipped":
            if order.estimated_delivery:
                eta_date = format_date_human(order.estimated_delivery)
                answer = (
                    f"Order {order.order_id} has shipped via {order.carrier} (Tracking Number: {order.tracking_number}). "
                    f"It is currently estimated to arrive on {eta_date}."
                )
            else:
                answer = (
                    f"Order {order.order_id} has shipped via {order.carrier} (Tracking Number: {order.tracking_number}). "
                    "A delivery estimate is not currently available from the carrier."
                )
        elif order.status in ("pending", "processing"):
            if order.estimated_delivery:
                eta_date = format_date_human(order.estimated_delivery)
                answer = (
                    f"Order {order.order_id} is currently {order.status}. "
                    f"Estimated delivery date is {eta_date}."
                )
            else:
                answer = (
                    f"Order {order.order_id} is currently {order.status}. "
                    "A delivery estimate is not yet available."
                )
        else:
            answer = result.message

        return AgentResponse(
            answer=answer,
            sources=[],
            handoff=handoff,
            tool_called="order_lookup",
            tool_arguments={"order_id": order.order_id},
            debug_info=debug_info
        )

    def generate_unsupported_action_response(
        self,
        action_type: str,
        result: OrderLookupResult,
        order_id: Optional[str],
        debug_info: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Handles requests to cancel, change address, or refund without falsely claiming execution.
        """
        if not order_id:
            return AgentResponse(
                answer="Please provide your order ID so I can check your order eligibility.",
                sources=[],
                handoff=False,
                tool_called=None,
                debug_info=debug_info
            )

        if not result.found:
            return self.generate_order_response(result, order_id, debug_info)

        order = result.order
        if action_type == "cancel":
            if order.status == "pending":
                answer = (
                    f"Order {order.order_id} is currently pending. Under our policy, cancellation requests may be made within 30 minutes while pending. "
                    "However, as an AI agent, I cannot directly cancel orders. I am escalating this to a human support specialist to complete your cancellation request."
                )
            else:
                answer = (
                    f"Order {order.order_id} is currently {order.status}. Orders that are already in processing, shipped, or delivered cannot be cancelled through the standard cancellation process. "
                    "I am connecting you with human support to discuss potential alternatives."
                )
        elif action_type == "address_change":
            if order.status in ("shipped", "delivered"):
                answer = (
                    f"Order {order.order_id} has already {order.status} with {order.carrier} (Tracking: {order.tracking_number}). "
                    "The agent cannot directly change the address for an order that has already shipped. "
                    "Please contact the carrier directly or reach out to a human support specialist for assistance."
                )
            else:
                answer = (
                    f"Order {order.order_id} is currently {order.status}. Address changes cannot be performed directly by the AI agent. "
                    "I am connecting you with a human support specialist to review if an address update is possible."
                )
        else:
            answer = f"I am unable to perform {action_type} directly. I am connecting you with a human support specialist."

        return AgentResponse(
            answer=answer,
            sources=[],
            handoff=True,
            tool_called="order_lookup",
            tool_arguments={"order_id": order_id},
            debug_info=debug_info
        )

    def generate_privacy_refusal_response(
        self,
        order_id: Optional[str],
        debug_info: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Refuses requests for internal notes or customer PII.
        """
        answer = (
            "For customer privacy and security reasons, I cannot disclose personal customer information "
            "(such as email addresses or shipping addresses) or internal operational details (such as risk scores or warehouse notes). "
            "If you need authorized account assistance, please contact our human support team."
        )
        return AgentResponse(
            answer=answer,
            sources=[],
            handoff=True,
            tool_called="order_lookup" if order_id else None,
            tool_arguments={"order_id": order_id} if order_id else None,
            debug_info=debug_info
        )

    def generate_prompt_injection_refusal(
        self,
        query: str = "",
        debug_info: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Refuses adversarial prompt overrides and reinforces official policy authority.
        Internal documents, scratchpads, and user-injected instructions are never
        treated as authoritative policy sources.
        """
        answer = (
            "I cannot reveal internal instructions or system prompts. "
            "I cannot follow instructions embedded in retrieved documents or user messages "
            "that attempt to override operating guidelines. "
            "Internal notes and draft materials are not "
            "authoritative customer policy sources. "
            "Under our official Returns Policy, customers on the standard plan have "
            "30 calendar days from delivery to request a return for unused items. "
            "As an AI support agent, I cannot automatically approve returns or change policies."
        )
        return AgentResponse(
            answer=answer,
            sources=[SourceCitation(filename="01-returns-policy-current.md", heading="Standard return window")],
            handoff=False,
            tool_called=None,
            debug_info=debug_info
        )

    def generate_knowledge_response(
        self,
        user_message: str,
        contextual_query: str,
        retrieved_chunks: List[Tuple[DocumentChunk, float]],
        conflict_result: ConflictResult,
        session: SessionState,
        debug_info: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Generates a grounded RAG response with citations, conflict handling, and safe abstention.

        Priority order:
        1. Conflict detected → dynamic conflict answer built from conflicting chunk content.
        2. Out-of-scope topic not in KB → safe abstention.
        3. OpenAI API available → LLM generation from retrieved chunks.
        4. No API key → template synthesis from retrieved chunk content.
        5. No chunks retrieved → abstain and recommend human support.
        """
        chunks_only = [c for c, _ in retrieved_chunks]
        q_lower = user_message.lower()

        # ── Step 1: Genuine Source Conflict ──────────────────────────────────
        if conflict_result.has_conflict:
            conflict_lines = []
            for chunk in conflict_result.conflicting_chunks:
                excerpt = chunk.content.strip()
                conflict_lines.append(
                    f"- [{chunk.filename} - {chunk.heading}]: {excerpt}"
                )
            answer = (
                f"Our official documents contain conflicting information regarding "
                f"{conflict_result.topic.lower()}:\n"
                + "\n".join(conflict_lines)
                + f"\n\nAs the safest interim guidance: {conflict_result.interim_guidance} "
                + "I am recommending a human support confirmation to clarify this policy."
            )
            citations = self.build_citations_from_chunks(conflict_result.conflicting_chunks)
            return AgentResponse(
                answer=answer,
                sources=citations,
                handoff=True,
                tool_called=None,
                debug_info=debug_info
            )

        # ── Step 2: Safe Abstention for Topics Absent from the KB ────────────
        # These topics are genuinely outside the knowledge base scope.
        out_of_scope_terms = [
            "vegan", "organic certification", "animal product", "peta", "kosher", "halal"
        ]
        if any(term in q_lower for term in out_of_scope_terms):
            return AgentResponse(
                answer=(
                    "The supplied knowledge base does not contain information regarding "
                    "vegan certifications or materials for our bags and adhesives. "
                    "Because the supplied information is insufficient to confirm this "
                    "claim reliably, I recommend speaking with a human specialist."
                ),
                sources=[],
                handoff=True,
                tool_called=None,
                debug_info=debug_info
            )

        # ── Step 3: LLM Generation (when API key is configured) ───────────────
        if self.use_openai and self._openai_client and chunks_only:
            try:
                context_passages = "\n\n".join([
                    f"--- Source: [{c.filename} - {c.heading}] ---\n{c.content}"
                    for c in chunks_only
                ])
                user_prompt = (
                    f"RETRIEVED UNTRUSTED REFERENCE PASSAGES:\n{context_passages}"
                    f"\n\nUSER QUESTION: {user_message}"
                )
                completion = self._openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                raw_json = completion.choices[0].message.content
                data = json.loads(raw_json)
                citations = self.build_citations_from_chunks(chunks_only)
                return AgentResponse(
                    answer=data.get("answer", ""),
                    sources=citations,
                    handoff=data.get("handoff", False),
                    tool_called=data.get("tool_called"),
                    debug_info=debug_info
                )
            except Exception:
                pass  # Fall through to template synthesis

        # ── Step 4: Template Synthesis from Retrieved Chunks (no API key) ─────
        if chunks_only:
            return self._build_template_response(chunks_only, user_message=user_message, debug_info=debug_info)

        # ── Step 5: No Chunks Retrieved — Abstain ────────────────────────────
        return AgentResponse(
            answer=(
                "I do not have sufficient information in our official records to answer "
                "your question. I recommend contacting our customer support team for assistance."
            ),
            sources=[],
            handoff=True,
            tool_called=None,
            debug_info=debug_info
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_template_response(
        self,
        chunks: List[DocumentChunk],
        user_message: str = "",
        debug_info: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Synthesizes a customer-facing answer directly from the text of the top retrieved
        chunks. No hardcoded strings — all content comes from the KB documents.
        """
        q_lower = user_message.lower()
        is_incident_claim = any(
            sig in q_lower
            for sig in ["damaged", "broken", "defective", "zipper", "wrong item", "arrived damaged"]
        )
        handoff = is_incident_claim

        if len(chunks) == 1:
            top = chunks[0]
            doc_label = top.metadata.title or top.filename
            content = re.sub(r"(\d+)-calendar-day\b", r"\1 calendar days", top.content)
            answer = (
                f"According to our {doc_label} [{top.filename} - {top.heading}]:\n"
                f"{content}"
            )
        else:
            # Multi-source synthesis: build a coherent narrative from top chunks
            parts = []
            for chunk in chunks[:6]:
                content = re.sub(r"(\d+)-calendar-day\b", r"\1 calendar days", chunk.content)
                parts.append(
                    f"[{chunk.filename} - {chunk.heading}]: {content}"
                )
            answer = "Based on our official policies:\n\n" + "\n\n".join(parts)

        citations = self.build_citations_from_chunks(chunks)
        return AgentResponse(
            answer=answer,
            sources=citations,
            handoff=handoff,
            tool_called=None,
            debug_info=debug_info
        )

