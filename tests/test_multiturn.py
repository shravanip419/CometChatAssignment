import pytest
from app.agent.agent import SupportAgent


def test_multiturn_canada_followup():
    agent = SupportAgent()
    session_id = "test_session_canada"
    
    # Turn 1
    res1 = agent.process_message("Do you ship internationally?", session_id=session_id)
    assert "canada" in res1.answer.lower()
    
    # Turn 2: Follow-up question referencing Canada
    res2 = agent.process_message("What about Canada, and how long does it take?", session_id=session_id)
    ans2 = res2.answer.lower()
    assert "5–9 business days" in res2.answer or "5-9 business days" in ans2 or "5 to 9" in ans2
    assert "duties" in ans2 or "taxes" in ans2
    assert any(s.filename == "06-international-shipping.md" for s in res2.sources)
    assert res2.handoff is False


def test_multiturn_order_followup():
    agent = SupportAgent()
    session_id = "test_session_order"
    
    # Turn 1: Lookup order
    res1 = agent.process_message("Where is ORD-1007?", session_id=session_id)
    assert "shipped" in res1.answer.lower()
    
    # Turn 2: Follow-up asking when it will arrive without repeating order ID
    res2 = agent.process_message("When will it arrive?", session_id=session_id)
    assert "2026-08-22" in res2.answer or "August 22, 2026" in res2.answer
    assert res2.tool_called == "order_lookup"
