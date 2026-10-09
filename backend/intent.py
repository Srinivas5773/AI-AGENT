import re
from typing import Dict, Any, Optional

GREETING_PATTERNS = [
    r"^\s*(hi|hello|hey|greetings|howdy|good\s*(morning|afternoon|evening|day)|hi\s*there|hello\s*there)\s*[\.!\?]*\s*$",
]

THANKS_PATTERNS = [
    r"^\s*(thanks|thank\s*you|thank\s*you\s*so\s*much|thanks\s*a\s*lot|thank\s*you\s*very\s*much|ty)\s*[\.!\?]*\s*$",
]

CLOSING_PATTERNS = [
    r"^\s*(bye|goodbye|see\s*you|ok|okay|sure|got\s*it|awesome|cool|great)\s*[\.!\?]*\s*$",
]

NON_ACADEMIC_PATTERNS = [
    r"^\s*(what['’]?s\s*the\s*weather|tell\s*me\s*a\s*joke|who\s*won\s*the|what\s*is\s*your\s*name)\s*[\.!\?]*\s*$",
]


def classify_conversational_intent(text: str) -> Optional[Dict[str, Any]]:
    """Classifies simple conversational intents (greetings, thanks, closings, non-academic)
    before initiating RAG retrieval, tool calling, or escalation.
    """
    clean_text = text.strip().lower()

    # Check Greetings
    for pattern in GREETING_PATTERNS:
        if re.match(pattern, clean_text, re.IGNORECASE):
            return {
                "type": "greeting",
                "answer": "Hello! I am your AI Student Academic Support Agent. How can I assist you with your course syllabi, exam schedules, academic calendar, or college rules today?",
                "tools_used": [],
                "citations": [],
                "success": True,
                "mode": "conversational_intent",
            }

    # Check Thanks
    for pattern in THANKS_PATTERNS:
        if re.match(pattern, clean_text, re.IGNORECASE):
            return {
                "type": "thanks",
                "answer": "You're very welcome! Please let me know if you have any other questions regarding your courses, exam schedules, or academic guidelines.",
                "tools_used": [],
                "citations": [],
                "success": True,
                "mode": "conversational_intent",
            }

    # Check Closings
    for pattern in CLOSING_PATTERNS:
        if re.match(pattern, clean_text, re.IGNORECASE):
            return {
                "type": "closing",
                "answer": "Good luck with your studies! Feel free to ask whenever you need academic assistance.",
                "tools_used": [],
                "citations": [],
                "success": True,
                "mode": "conversational_intent",
            }

    # Check Non-Academic Casual Inputs
    for pattern in NON_ACADEMIC_PATTERNS:
        if re.match(pattern, clean_text, re.IGNORECASE):
            return {
                "type": "non_academic",
                "answer": "I specialize in college academic support! I can help you with your course syllabi, exam dates, room numbers, reporting guidelines, or connecting you with human staff if needed. What academic information do you need?",
                "tools_used": [],
                "citations": [],
                "success": True,
                "mode": "conversational_intent",
            }

    return None
