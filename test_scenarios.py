"""Simple scripted scenarios to exercise MedEquipChatbot.

This is not a formal test suite yet, but it demonstrates a couple of
end-to-end flows using the current rule-based implementation.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env in the project root so config.py
# and database.py pick up MEDEQUIP_DB_* values correctly when imported.
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

from chatbot import MedEquipChatbot
from database import initialize_database


def run_scenarios() -> None:
    initialize_database()
    bot = MedEquipChatbot()

    print("== UC9: General Support (No Auth) ==")
    msg = "What are your support hours?"
    print("You:", msg)
    print("Assistant:", bot.chat(msg))
    print()

    print("== UC1: Order Tracking (Auth Required) ==")
    # Authenticate as the seeded demo client
    bot.authenticate("contact@cityhospital.com", "ME-10001")
    msg = "When will my order ORD-2024-0001 arrive?"
    print("You:", msg)
    print("Assistant:", bot.chat(msg))


if __name__ == "__main__":
    run_scenarios()
