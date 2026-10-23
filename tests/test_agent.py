"""Comprehensive tests for Phase 3 VoiceOpsAgent multi-turn conversation and tools."""
import pytest
from unittest.mock import MagicMock
from src.agent import VoiceOpsAgent
from src.conversation import ConversationState
from src.retrieval import RetrievalResult
from src.answering import GroundedAnswer


@pytest.fixture
def mock_tools():
    tools = MagicMock()
    # Default mock lookup responses
    def mock_lookup(order_id, verification_value=None):
        if str(order_id) == "99999999":
            return {"verified": False, "verification_required": True, "message": "Verification failed or order not found."}
        if verification_value is None:
            return {"verification_required": True, "order_id": order_id, "message": "Verification required."}
        if str(verification_value) == "4533":
            return {
                "found": True,
                "verified": True,
                "order_id": order_id,
                "customer_id": "C100181",
                "customer_first_name": "Kabir",
                "status": "delivered",
                "delivery_pincode": "781006",
                "delivered_on": "2026-10-15",
                "placed_at": "2026-10-05T08:05",
                "is_plus": False,
                "payment_method": "upi",
                "contacts_last_7_days": 0,
                "items": [
                    {"order_id": order_id, "sku": "ELE-0021", "title": "4K Smart TV", "return_category": "electronics", "unit_price_inr": 31649}
                ],
            }
        return {"verified": False, "verification_required": True, "message": "Verification failed or order not found."}

    tools.lookup_order.side_effect = mock_lookup

    def mock_ticket(summary, order_id=None, reason=None, intent=None):
        if not summary or len(summary.strip()) < 20:
            return {"created": False, "error": "summary too short"}
        return {"created": True, "ticket_id": "TKT1234567890abcdef"}

    tools.create_ticket.side_effect = mock_ticket
    return tools


@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    retriever.chunks = [MagicMock()]
    retriever.retrieve.return_value = [
        RetrievalResult(
            chunk_id="pol_returns_v4.md:RET-2:0",
            source_file="pol_returns_v4.md",
            section_id="RET-2",
            title="Returns policy",
            heading="Return windows by category",
            text="Electronics have a 7-day return window.",
            score=0.88,
        )
    ]
    return retriever


@pytest.fixture
def mock_generator():
    generator = MagicMock()
    generator.generate_answer.return_value = GroundedAnswer(
        question="Can I return electronics?",
        answer="Electronics can be returned within 7 days under current policy.",
        decision="answer",
        is_grounded=True,
        insufficient_evidence=False,
        evidence_sources=["RET-2"],
    )
    return generator


@pytest.fixture
def agent(mock_retriever, mock_generator, mock_tools):
    return VoiceOpsAgent(
        retriever=mock_retriever,
        answer_generator=mock_generator,
        tools_adapter=mock_tools,
    )


def test_first_turn_introduces_ai(agent):
    """Verifies that the agent introduces itself as AI assistant on turn 1."""
    turn = agent.handle_message("Hello, I need help with an order.", conversation_id="c1")
    assert turn.decision == "clarify"
    assert "AI assistant" in turn.agent_message or "एआई सहायक" in turn.agent_message
    assert "order number" in turn.agent_message or "ऑर्डर नंबर" in turn.agent_message


def test_state_isolation_between_conversations(agent):
    """Verifies that two different sessions do not leak order or verification state."""
    agent.handle_message("Order 8978 2837", conversation_id="session_A")
    state_a = agent.get_or_create_session("session_A")
    state_b = agent.get_or_create_session("session_B")

    assert state_a.order_id == "89782837"
    assert state_a.verification_status == "pending"
    assert state_b.order_id is None
    assert state_b.verification_status == "none"


def test_verification_required_before_private_order_disclosure(agent):
    """Proves that private order details are not disclosed upon simply giving order ID."""
    turn = agent.handle_message("My order is 8978 2837", conversation_id="c2")
    assert turn.decision == "clarify"
    # Must challenge for phone last 4 or pincode
    assert "last 4" in turn.agent_message.lower() or "pincode" in turn.agent_message.lower()
    # Must not leak customer name, items, or status
    assert "Kabir" not in turn.agent_message
    assert "Smart TV" not in turn.agent_message
    assert "delivered" not in turn.agent_message.lower()


def test_successful_verification_flow(agent):
    """Tests successful identity verification with phone last 4 digits."""
    agent.handle_message("Order 8978 2837", conversation_id="c3")
    turn = agent.handle_message("Last four digits are 4533", conversation_id="c3")
    assert turn.decision == "answer"
    assert "Kabir" in turn.agent_message or "verified" in turn.agent_message.lower()
    state = agent.get_or_create_session("c3")
    assert state.is_verified is True


def test_failed_verification_retry_and_lockout(agent):
    """Tests single retry allowance and subsequent lockout upon double failure."""
    agent.handle_message("Order 8978 2837", conversation_id="c4")

    # Attempt 1 (Wrong)
    turn1 = agent.handle_message("Last four digits are 0000", conversation_id="c4")
    assert turn1.decision == "clarify"
    assert "again" in turn1.agent_message.lower() or "दोबारा" in turn1.agent_message

    # Attempt 2 (Wrong again -> lockout)
    turn2 = agent.handle_message("Last four digits are 0000", conversation_id="c4")
    assert turn2.decision == "refuse"
    assert "cannot share" in turn2.agent_message.lower() or "साझा नहीं" in turn2.agent_message

    state = agent.get_or_create_session("c4")
    assert state.verification_status == "failed"

    # Subsequent request about order details is refused
    turn3 = agent.handle_message("Where is my order?", conversation_id="c4")
    assert turn3.decision == "refuse"
    assert "cannot share" in turn3.agent_message.lower() or "could not be completed" in turn3.agent_message.lower()


def test_unknown_order_handling(agent):
    """Verifies that an unknown order ID does not disclose details or crash."""
    turn = agent.handle_message("Check order 9999 9999", conversation_id="c5")
    assert turn.decision == "clarify"
    assert "99999999" in turn.agent_message

    # Customer tries verification on non-existent order
    turn_verify = agent.handle_message("Digits are 4533", conversation_id="c5")
    assert turn_verify.decision == "clarify"
    assert "again" in turn_verify.agent_message.lower() or "match" in turn_verify.agent_message.lower()


def test_high_value_damage_escalates_to_priority_team(agent):
    """Verifies that damaged item > ₹10,000 escalates to Priority Resolution team with ticket."""
    agent.handle_message("Order 8978 2837", conversation_id="c6")
    agent.handle_message("Last 4 digits 4533", conversation_id="c6")

    turn = agent.handle_message("The 4K Smart TV arrived damaged with a cracked screen.", conversation_id="c6")
    assert turn.decision == "escalate"
    assert "Priority Resolution" in turn.agent_message or "ticket" in turn.agent_message.lower()
    assert "TKT1234567890abcdef" in turn.agent_message
    assert "create_ticket()" in turn.tool_calls


def test_human_agent_request_escalation(agent):
    """Verifies that asking for a human generates a ticket and escalates."""
    agent.handle_message("Order 8978 2837", conversation_id="c7")
    agent.handle_message("4533", conversation_id="c7")

    turn = agent.handle_message("Can I speak to a human colleague please?", conversation_id="c7")
    assert turn.decision == "escalate"
    assert "ticket" in turn.agent_message.lower() or "colleague" in turn.agent_message.lower()
    assert "TKT1234567890abcdef" in turn.agent_message


def test_ticket_creation_failure_handling(agent, mock_tools):
    """Verifies that if ticket creation fails, the agent never claims success."""
    mock_tools.create_ticket.return_value = {"created": False, "error": "summary too short"}

    agent.handle_message("Order 8978 2837", conversation_id="c8")
    agent.handle_message("4533", conversation_id="c8")

    # If tool returns created=False, the agent must not claim success
    turn = agent.handle_message("Can I speak to a person?", conversation_id="c8")
    assert "TKT" not in turn.agent_message or "created" not in turn.agent_message


def test_rag_fallback_for_general_policy_questions(agent, mock_generator):
    """Verifies that general policy questions fall back to grounded RAG without exposing order data."""
    turn = agent.handle_message("Can I return electronics?", conversation_id="c9")
    assert turn.decision == "answer"
    assert "7 days" in turn.agent_message
    mock_generator.generate_answer.assert_called()


def test_no_fabricated_order_facts(agent):
    """Proves agent does not invent order numbers or verification values."""
    turn = agent.handle_message("I want a refund on my order", conversation_id="c10")
    # Must ask for order ID rather than fabricating an order
    assert turn.decision == "clarify"
    state = agent.get_or_create_session("c10")
    assert state.is_verified is False
    assert state.order_id is None
