"""State management for multi-turn ZentroMart VoiceOps conversations."""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ConversationTurn:
    turn_number: int
    user_message: str
    agent_message: str
    decision: str  # "answer", "clarify", "escalate", "refuse"
    tool_calls: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    intent: Optional[str] = None
    language: str = "en"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConversationState:
    """Maintains state across multiple turns in an isolated customer session."""
    conversation_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    order_id: Optional[str] = None
    verification_status: str = "none"  # "none", "pending", "verified", "failed"
    verification_attempts: int = 0
    verified_order_data: Optional[Dict[str, Any]] = None
    tickets: List[Dict[str, Any]] = field(default_factory=list)
    current_intent: Optional[str] = None
    language: str = "en"

    @property
    def is_verified(self) -> bool:
        return self.verification_status == "verified" and self.verified_order_data is not None

    def record_turn(
        self,
        user_message: str,
        agent_message: str,
        decision: str,
        tool_calls: Optional[List[str]] = None,
        evidence_sources: Optional[List[str]] = None,
        intent: Optional[str] = None,
        language: Optional[str] = None,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            turn_number=len(self.turns) + 1,
            user_message=user_message,
            agent_message=agent_message,
            decision=decision,
            tool_calls=tool_calls or [],
            evidence_sources=evidence_sources or [],
            intent=intent or self.current_intent,
            language=language or self.language,
        )
        self.turns.append(turn)
        return turn

    def get_history_summary(self, max_turns: int = 6) -> str:
        """Returns a concise text summary of recent turns for LLM prompt context."""
        recent = self.turns[-max_turns:]
        lines = []
        for t in recent:
            lines.append(f"Turn {t.turn_number}:")
            lines.append(f"  Customer: {t.user_message}")
            lines.append(f"  Assistant ({t.decision}): {t.agent_message}")
        return "\n".join(lines)
