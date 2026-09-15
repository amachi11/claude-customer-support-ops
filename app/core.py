from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List
import re
import time
import os

POLICIES = {
    "returns": "Standard items may be returned within 30 days. Electronics may be returned within 14 days. Final-sale items are non-refundable.",
    "delayed": "If a shipment is delayed, support should provide the latest carrier status. Refunds over $50 require human approval unless the shipment is confirmed lost.",
    "refunds": "Refunds under $50 may be auto-approved when policy conditions are met. Refunds from $50 to $250 require human approval. Refunds above $250 require supervisor escalation.",
}

ORDERS = {
    "NC-48392": {"status": "Delayed", "eta": "September 16", "carrier": "FedEx", "value": 129.99},
    "NC-10001": {"status": "Delivered", "eta": "September 10", "carrier": "UPS", "value": 35.00},
}

@dataclass
class ConversationState:
    conversation_id: str
    facts: Dict[str, str] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)

class SupportEngine:
    def __init__(self) -> None:
        self.states: Dict[str, ConversationState] = {}
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "").strip()

    def _state(self, conversation_id: str) -> ConversationState:
        return self.states.setdefault(conversation_id, ConversationState(conversation_id))

    def _extract_facts(self, text: str, state: ConversationState) -> None:
        order = re.search(r"\bNC-\d{5}\b", text.upper())
        if order:
            state.facts["order_id"] = order.group(0)
        address_match = re.search(r"(?:send|ship|use).{0,20}(?:to|address)\s+([^.!?]+)", text, flags=re.I)
        if address_match:
            state.facts["shipping_address"] = address_match.group(1).strip()

    def _detect_injection(self, text: str) -> bool:
        t = text.lower()
        patterns = ["ignore all previous instructions", "ignore previous instructions", "i'm an administrator", "i am an administrator", "reveal system prompt"]
        return any(p in t for p in patterns)

    def _intent(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ["refund", "money back"]): return "refund"
        if any(k in t for k in ["where is", "hasn't arrived", "has not arrived", "delayed", "late"]): return "order_status"
        if any(k in t for k in ["return", "45 days"]): return "returns"
        if any(k in t for k in ["cancel subscription", "cancel my subscription"]): return "subscription_cancel"
        return "general"

    def _claude_available(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_model)

    def _claude_reply(self, system_prompt: str, user_message: str) -> str | None:
        if not self._claude_available():
            return None
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=self.anthropic_api_key)
            msg = client.messages.create(
                model=self.anthropic_model,
                max_tokens=500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            if msg.content and getattr(msg.content[0], "text", None):
                return msg.content[0].text.strip()
        except Exception:
            return None
        return None

    def chat(self, conversation_id: str, message: str) -> dict:
        started = time.perf_counter()
        state = self._state(conversation_id)
        self._extract_facts(message, state)
        state.history.append({"role": "user", "content": message})

        if self._detect_injection(message):
            reply = "I can help with your support request, but I can't override internal policies or expose protected instructions."
            result = {"intent": "security", "reply": reply, "escalated": False, "reason": "prompt_injection_blocked", "context": []}
        else:
            intent = self._intent(message)
            order_id = state.facts.get("order_id")
            order = ORDERS.get(order_id) if order_id else None
            context = []
            escalated = False
            reason = None

            if intent == "order_status" and order:
                context = [f"order:{order_id}", "policy:delayed"]
                reply = f"Order {order_id} is currently {order['status'].lower()} with {order['carrier']}. The latest estimated delivery date is {order['eta']}."
            elif intent == "refund" and order:
                context = [f"order:{order_id}", "policy:refunds", "policy:delayed"]
                value = float(order["value"])
                if value < 50:
                    reply = f"Order {order_id} is valued at ${value:.2f}. Based on the refund policy, this request can be reviewed for automatic approval if the policy conditions are met."
                elif value <= 250:
                    escalated, reason = True, "refund_requires_human_approval"
                    reply = f"I found order {order_id} (${value:.2f}). Because refunds between $50 and $250 require human approval, I've flagged this request for a support agent instead of claiming the refund is complete."
                else:
                    escalated, reason = True, "high_value_refund"
                    reply = f"Order {order_id} is above the automated refund threshold, so this needs supervisor review."
            elif intent == "returns":
                context = ["policy:returns"]
                reply = "Standard items can be returned within 30 days, while electronics have a 14-day return window. Final-sale items are non-refundable."
            elif "chargeback" in message.lower() or "contacted you four times" in message.lower():
                escalated, reason = True, "high_risk_customer_escalation"
                reply = "This issue needs a human support specialist because it involves repeated unresolved contact or chargeback risk. I've marked it as high priority."
            else:
                context = [f"memory:{k}" for k in state.facts]
                if order_id and order:
                    reply = f"I still have order {order_id} in context. Tell me what you'd like to do next and I'll use the order details and applicable support policy."
                else:
                    reply = "I can help with order status, returns, refunds, subscription issues, and escalation. Please share an order number such as NC-48392 when relevant."

            result = {"intent": intent, "reply": reply, "escalated": escalated, "reason": reason, "context": context}

        if self._claude_available() and not result.get("escalated") and result.get("reason") != "prompt_injection_blocked":
            grounding = "\n".join(result.get("context", [])) or "No external context"
            system_prompt = (
                "You are a customer-support assistant. Preserve every policy fact and authorization boundary "
                "from the supplied draft. Never claim an action happened unless the draft says it happened. "
                "Respond concisely and professionally.\nGrounding: " + grounding
            )
            refined = self._claude_reply(system_prompt, f"Customer: {message}\nApproved draft: {result['reply']}")
            if refined:
                result["reply"] = refined

        state.history.append({"role": "assistant", "content": result["reply"]})
        result["conversation_id"] = conversation_id
        result["memory"] = dict(state.facts)
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["mode"] = "claude" if self._claude_available() else "deterministic_demo"
        return result
