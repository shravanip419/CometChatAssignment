from typing import Optional, Dict, Any
from app.models.schemas import AgentResponse
from app.rag.retriever import KnowledgeRetriever
from app.tools.order_lookup import OrderLookupTool
from app.agent.state import SessionManager, SessionState
from app.agent.router import RequestRouter, IntentType, RouteDecision
from app.agent.response_generator import ResponseGenerator
from app.utils import format_date_human
from app.agent.safety_validator import SafetyValidator
from app.config import OPENAI_API_KEY, OPENAI_MODEL, DEBUG_MODE


class SupportAgent:
    """
    Thin orchestrator for Aster & Row Customer Support.
    Coordinates Session State, Request Routing, Knowledge Retrieval,
    Order Data Access, Grounded Generation, and Safety Validation.
    """
    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
        order_tool: Optional[OrderLookupTool] = None,
        session_manager: Optional[SessionManager] = None,
        router: Optional[RequestRouter] = None,
        generator: Optional[ResponseGenerator] = None,
        safety_validator: Optional[SafetyValidator] = None,
        api_key: Optional[str] = None,
        model: str = OPENAI_MODEL,
        debug: bool = DEBUG_MODE
    ):
        self.retriever = retriever or KnowledgeRetriever()
        self.order_tool = order_tool or OrderLookupTool()
        self.session_manager = session_manager or SessionManager()
        self.router = router or RequestRouter()
        self.generator = generator or ResponseGenerator(api_key=api_key or OPENAI_API_KEY, model=model)
        self.safety_validator = safety_validator or SafetyValidator()
        self.debug = debug

    def process_message(self, user_message: str, session_id: str = "default") -> AgentResponse:
        """
        Processes a single conversational turn through the 7-stage agent pipeline.
        """
        # 1. State Retrieval & Turn Recording
        session: SessionState = self.session_manager.get_or_create_session(session_id)
        session.add_user_message(user_message)

        debug_info: Dict[str, Any] = {
            "session_id": session_id,
            "raw_user_message": user_message,
            "history_length": len(session.messages),
        }

        # 2. Request Routing
        decision: RouteDecision = self.router.route(user_message, session)
        debug_info["route_decision"] = decision.model_dump()

        # 3. Execution & Response Generation by Intent
        if decision.intent == IntentType.PROMPT_INJECTION:
            response = self.generator.generate_prompt_injection_refusal(query=user_message, debug_info=debug_info if self.debug else None)

        elif decision.intent == IntentType.PRIVACY_REQUEST:
            response = self.generator.generate_privacy_refusal_response(decision.order_id, debug_info=debug_info if self.debug else None)

        elif decision.intent == IntentType.UNSUPPORTED_ACTION:
            tool_res = self.order_tool.lookup(decision.order_id) if decision.order_id else None
            if tool_res:
                debug_info["sanitized_tool_result"] = tool_res.model_dump()
            response = self.generator.generate_unsupported_action_response(
                decision.action_type or "action",
                tool_res,
                decision.order_id,
                debug_info=debug_info if self.debug else None
            )

        elif decision.intent == IntentType.ORDER_LOOKUP:
            if decision.is_missing_order_id:
                response = self.generator.generate_order_response(None, None, debug_info=debug_info if self.debug else None)
            else:
                tool_res = self.order_tool.lookup(decision.order_id)
                debug_info["sanitized_tool_result"] = tool_res.model_dump()
                response = self.generator.generate_order_response(tool_res, decision.order_id, debug_info=debug_info if self.debug else None)

        else:
            # IntentType.KNOWLEDGE_BASE
            contextual_query = session.get_contextual_query(user_message)
            debug_info["contextual_query"] = contextual_query

            retrieved_chunks = self.retriever.retrieve(contextual_query, top_k=6)
            conflict_result = self.retriever.check_conflicts([c for c, _ in retrieved_chunks], query=contextual_query)
            debug_info["retrieved_chunks"] = [
                {"chunk_id": c.chunk_id, "filename": c.filename, "heading": c.heading, "score": score}
                for c, score in retrieved_chunks
            ]
            debug_info["conflict_detected"] = conflict_result.has_conflict

            response = self.generator.generate_knowledge_response(
                user_message,
                contextual_query,
                retrieved_chunks,
                conflict_result,
                session,
                debug_info=debug_info if self.debug else None
            )

        # 4. Safety & Privacy Post-Validation
        validated_response = self.safety_validator.validate(response)

        # 5. State Update
        session.add_assistant_message(validated_response.answer)

        return validated_response
