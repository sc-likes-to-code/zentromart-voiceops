"""Adapter for synthetic ZentroMart customer-support mock tools.

Gates all order details behind caller verification and enforces validation rules.
"""
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import DATASET_DIR

# Ensure dataset root is on sys.path for importing tools
_DATASET_STR = str(DATASET_DIR)
if _DATASET_STR not in sys.path:
    sys.path.insert(0, _DATASET_STR)

try:
    from tools.tools import create_ticket as _raw_create_ticket
    from tools.tools import lookup_order as _raw_lookup_order
except ImportError:
    # Fallback to direct import
    sys.path.insert(0, str(DATASET_DIR / "tools"))
    from tools import create_ticket as _raw_create_ticket
    from tools import lookup_order as _raw_lookup_order


class ToolsAdapter:
    """Safe gateway for mock customer support tools."""

    @staticmethod
    def lookup_order(order_id: str, verification_value: Optional[str] = None) -> Dict[str, Any]:
        """Look up order details.
        
        Without a valid verification_value, no private order details are returned.
        """
        oid = "".join(ch for ch in str(order_id) if "0" <= ch <= "9")
        proof = (
            "".join(ch for ch in str(verification_value) if "0" <= ch <= "9")
            if verification_value is not None
            else None
        )
        return _raw_lookup_order(oid, verification_value=proof)

    @staticmethod
    def create_ticket(
        summary: str,
        order_id: Optional[str] = None,
        reason: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a synthetic customer support ticket.
        
        Summary must be >= 20 characters to succeed.
        """
        return _raw_create_ticket(
            summary=summary,
            order_id=order_id,
            reason=reason,
            intent=intent,
        )
