"""Core MedEquipChatbot logic and simple CLI interface.

This is a first-pass implementation aligned with the project
specification. Many behaviors are intentionally simple or stubbed so
that they can be replaced with LLM-powered flows later.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from config import ENABLE_RAG, MAX_HISTORY_TURNS
from database import get_client_by_credentials, initialize_database
from rag_pipeline import search_knowledge


@dataclass
class AuthenticatedClient:
    client_id: str
    name: str
    email: str


@dataclass
class ConversationTurn:
    user: str
    assistant: str


@dataclass
class MedEquipChatbot:
    """Main chatbot class coordinating DB + RAG calls.

    For now, intent classification and SQL generation use simple rule-
    based logic that will later be upgraded to LLM prompts.
    """

    authenticated_client: Optional[AuthenticatedClient] = None
    history: list[ConversationTurn] = field(default_factory=list)

    # --- Authentication ---

    def authenticate(self, email: str, client_id: str) -> bool:
        client = get_client_by_credentials(email=email, client_id=client_id)
        if not client:
            return False
        self.authenticated_client = AuthenticatedClient(
            client_id=client.client_id,
            name=client.name,
            email=client.email,
        )
        return True

    # --- Intent classification (placeholder) ---

    def classify_intent(self, message: str) -> Dict[str, Any]:
        """Very simple heuristic intent classifier.

        This mirrors the JSON structure from the spec but uses keyword
        matching for now so we can exercise routing early.
        """

        text = message.lower()
        intent = "GENERAL_SUPPORT"
        requires_auth = False
        data_source = "RAG"
        entities: Dict[str, Any] = {}

        # Extract common IDs if present
        for token in message.split():
            if token.startswith("ORD-"):
                entities["order_id"] = token
            if token.startswith("TKT-"):
                entities["ticket_id"] = token
            if token.startswith("INV-"):
                entities["invoice_id"] = token
            if token.startswith("ME-"):
                entities["client_id"] = token
            if token.startswith("US-") or token.startswith("CT-"):
                entities["serial_number"] = token

        if any(word in text for word in ["order", "shipment", "delivery", "tracking"]):
            intent = "ORDER_DELIVERY"
            requires_auth = True
            data_source = "SQL"
        elif any(word in text for word in ["spec", "specification", "manual", "power requirements"]):
            intent = "PRODUCT_INFO"
            requires_auth = False
            data_source = "RAG"
        elif any(word in text for word in ["warranty", "amc", "maintenance"]):
            intent = "WARRANTY_AMC"
            requires_auth = True
            data_source = "SQL"
        elif any(word in text for word in ["ticket", "issue", "problem", "error"]):
            intent = "ISSUE_RESOLUTION"
            requires_auth = True
            data_source = "BOTH"
        elif any(word in text for word in ["invoice", "payment", "bill"]):
            intent = "FINANCIAL"
            requires_auth = True
            data_source = "SQL"
        elif any(word in text for word in ["part", "spare", "stock"]):
            intent = "SPARE_PARTS"
            requires_auth = True
            data_source = "SQL"
        elif any(word in text for word in ["fda", "ce", "iso", "compliance"]):
            intent = "COMPLIANCE"
            requires_auth = False
            data_source = "RAG"
        elif any(word in text for word in ["hours", "contact", "phone", "support"]):
            intent = "GENERAL_SUPPORT"
            requires_auth = False
            data_source = "RAG"

        return {
            "primary_intent": intent,
            "requires_auth": requires_auth,
            "data_source": data_source,
            "entities": entities,
        }

    # --- SQL generation stubs ---

    def generate_sql(self, request: str, entities: Dict[str, Any]) -> Optional[str]:
        """Return a simple SQL query for common scenarios.

        This is a rule-based stand-in for the LLM SQL generator.
        """

        text = request.lower()
        order_id = entities.get("order_id")
        ticket_id = entities.get("ticket_id")
        invoice_id = entities.get("invoice_id")
        serial_number = entities.get("serial_number")
        client_id = entities.get("client_id") or (self.authenticated_client.client_id if self.authenticated_client else None)

        if "order" in text and order_id:
            return (
                "SELECT o.order_id, o.status, s.delivery_status, s.expected_delivery_date "
                "FROM orders o LEFT JOIN shipments s ON o.order_id = s.order_id "
                "WHERE o.order_id = %s AND o.client_id = %s"
            )
        if "ticket" in text and ticket_id:
            return (
                "SELECT t.ticket_id, t.status, h.event_time, h.status AS history_status, h.notes "
                "FROM support_tickets t LEFT JOIN ticket_history h ON t.ticket_id = h.ticket_id "
                "WHERE t.ticket_id = %s AND t.client_id = %s ORDER BY h.event_time DESC"
            )
        if "invoice" in text and invoice_id:
            return (
                "SELECT invoice_id, client_id, order_id, amount, issue_date, due_date, status "
                "FROM invoices WHERE invoice_id = %s AND client_id = %s"
            )
        if "warranty" in text and serial_number:
            return (
                "SELECT w.warranty_id, w.serial_number, w.start_date, w.end_date, w.coverage_level "
                "FROM warranties w WHERE w.serial_number = %s"
            )
        if any(word in text for word in ["part", "spare", "stock"]):
            return (
                "SELECT part_number, name, description, stock_quantity, unit_price "
                "FROM parts_catalog WHERE name LIKE %s"
            )

        # Fallback: no SQL needed
        return None

    def execute_sql_query(self, sql: str, entities: Dict[str, Any]):
        """Execute a generated SQL query with best-effort parameter binding."""

        from database import execute_query

        params = []
        text = sql.lower()
        if "where o.order_id" in text:
            params = [entities.get("order_id"), self.authenticated_client.client_id]
        elif "where t.ticket_id" in text:
            params = [entities.get("ticket_id"), self.authenticated_client.client_id]
        elif "where invoice_id" in text:
            params = [entities.get("invoice_id"), self.authenticated_client.client_id]
        elif "where w.serial_number" in text:
            params = [entities.get("serial_number")]
        elif "from parts_catalog" in text:
            product_name = entities.get("product_model") or "%%"
            params = [f"%{product_name}%"]

        return execute_query(sql, params)

    # --- Knowledge base ---

    def search_knowledge_base(self, query: str) -> str:
        snippets = search_knowledge(query)
        return "\n".join(snippets)

    # --- Response generation (non-LLM placeholder) ---

    def generate_response(
        self,
        message: str,
        intent: Dict[str, Any],
        sql_results,
        rag_context: str,
    ) -> str:
        """Format a human-readable response using simple templates.

        This will later be replaced with an LLM call.
        """

        primary = intent["primary_intent"]
        entities = intent["entities"]

        if primary == "ORDER_DELIVERY" and sql_results:
            row = sql_results[0]
            return (
                f"Order {row['order_id']} for client {self.authenticated_client.client_id} "
                f"is currently '{row['delivery_status'] or row['status']}'. "
                f"Expected delivery date: {row['expected_delivery_date']}"
            )
        if primary == "WARRANTY_AMC" and sql_results:
            row = sql_results[0]
            return (
                f"Serial {row['serial_number']} is covered under warranty {row['warranty_id']} "
                f"from {row['start_date']} to {row['end_date']} (level: {row['coverage_level']})."
            )
        if primary == "ISSUE_RESOLUTION" and sql_results:
            ticket_id = entities.get("ticket_id")
            latest = sql_results[0]
            return (
                f"Ticket {ticket_id} is currently '{latest['status']}'. "
                f"Most recent update at {latest['event_time']}: {latest['notes']}"
            )
        if primary == "FINANCIAL" and sql_results:
            row = sql_results[0]
            return (
                f"Invoice {row['invoice_id']} for order {row['order_id']} has status '{row['status']}' "
                f"and amount {row['amount']} (due {row['due_date']})."
            )
        if primary == "SPARE_PARTS" and sql_results:
            parts_lines = [
                f"{r['name']} (Part {r['part_number']}): {r['stock_quantity']} in stock at {r['unit_price']} each"
                for r in sql_results
            ]
            return "Available parts:\n" + "\n".join(parts_lines)

        # For RAG / general support, just echo snippets
        if rag_context:
            return rag_context

        return (
            "I'm not sure I can fully answer that yet, but here is what I found: "
            + json.dumps(intent, indent=2)
        )

    # --- Main chat entry point ---

    def chat(self, message: str) -> str:
        intent = self.classify_intent(message)

        # Enforce authentication when required
        if intent["requires_auth"] and not self.authenticated_client:
            return (
                "This request requires authentication. "
                "Please use the 'auth' command and provide your email and Client ID (ME-XXXXX)."
            )

        sql_results = []
        rag_context = ""

        sql = self.generate_sql(message, intent["entities"])
        if sql:
            sql_results = self.execute_sql_query(sql, intent["entities"])

        # Only perform RAG lookups if explicitly enabled in config.
        if ENABLE_RAG and intent["data_source"] in {"RAG", "BOTH"}:
            rag_context = self.search_knowledge_base(message)

        response = self.generate_response(message, intent, sql_results, rag_context)

        # Update history
        self.history.append(ConversationTurn(user=message, assistant=response))
        if len(self.history) > MAX_HISTORY_TURNS:
            self.history = self.history[-MAX_HISTORY_TURNS :]

        return response


# --- Simple CLI loop ---


def run_cli() -> None:
    """Run an interactive CLI chat loop for local testing."""

    # Ensure DB exists and has data
    initialize_database()

    bot = MedEquipChatbot()

    banner = "=" * 60
    print(banner)
    print("MedEquip Solutions Customer Support (Dev Demo)")
    print("Type 'quit' to exit, 'auth' to authenticate, 'history' to view last turns")
    print(banner)

    while True:
        user = input("You: ").strip()
        if not user:
            continue
        if user.lower() in {"quit", "exit"}:
            print("Assistant: Goodbye!")
            break
        if user.lower() == "history":
            for turn in bot.history[-10:]:
                print(f"You: {turn.user}")
                print(f"Assistant: {turn.assistant}")
            continue
        if user.lower() == "auth":
            email = input("Email: ").strip()
            client_id = input("Client ID (ME-XXXXX): ").strip()
            if bot.authenticate(email=email, client_id=client_id):
                print(f"System: ✓ Authenticated as {bot.authenticated_client.name} ({bot.authenticated_client.client_id})")
            else:
                print("System: Authentication failed. Please check your email and Client ID.")
            continue

        reply = bot.chat(user)
        print("Assistant:", reply)


if __name__ == "__main__":
    run_cli()
