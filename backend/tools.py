import json
from typing import Any, Dict, List, Optional

from backend.data_loader import (
    query_exam_schedule,
    query_course_details,
    query_exam_rules,
)
from backend.rag import get_rag_engine
from backend.escalation import create_escalation_ticket as create_ticket_in_db

# Approved tool names allowlist - now 5 tools
ALLOWED_TOOLS = [
    "get_exam_schedule",
    "get_course_details",
    "search_exam_rules",
    "search_academic_docs",
    "create_escalation_ticket",
]


def get_exam_schedule(
    student_id: Optional[str] = None,
    course_code: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool 1: Search the exam schedule CSV dataset by student ID, course code, or subject."""
    try:
        return query_exam_schedule(
            student_id=student_id, course_code=course_code, subject=subject
        )
    except Exception as e:
        return {
            "status": "error",
            "message": f"Execution error in get_exam_schedule tool: {str(e)}",
            "records": [],
            "count": 0,
        }


def get_course_details(
    course_code: Optional[str] = None,
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool 2: Retrieve course details (department, instructor, credits, prerequisites) from dataset."""
    try:
        return query_course_details(course_code=course_code, subject=subject)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Execution error in get_course_details tool: {str(e)}",
            "courses": [],
            "count": 0,
        }


def search_exam_rules(query: str) -> Dict[str, Any]:
    """Tool 3: Search relevant examination rules from the official rules document."""
    try:
        if not query or not str(query).strip():
            return {
                "status": "error",
                "message": "Rule search query cannot be empty.",
                "rules": [],
                "count": 0,
            }
        return query_exam_rules(query=str(query).strip())
    except Exception as e:
        return {
            "status": "error",
            "message": f"Execution error in search_exam_rules tool: {str(e)}",
            "rules": [],
            "count": 0,
        }


def search_academic_docs(query: str) -> Dict[str, Any]:
    """Tool 4 (RAG): Retrieve relevant passages, syllabi, calendar guidelines, and college documents."""
    try:
        if not query or not str(query).strip():
            return {"status": "error", "message": "RAG search query cannot be empty.", "results": [], "count": 0}
        rag_engine = get_rag_engine()
        return rag_engine.search(query=str(query).strip(), top_k=3)
    except Exception as e:
        return {"status": "error", "message": f"Execution error in search_academic_docs: {str(e)}", "results": [], "count": 0}


def create_escalation_ticket(
    reason: str,
    student_question: Optional[str] = None,
    evidence_summary: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool 5 (Escalation): Create a persistent human escalation ticket when human decision or review is required."""
    try:
        return create_ticket_in_db(
            student_question=student_question or "Unspecified student query",
            reason=reason or "Human intervention required",
            evidence_summary=evidence_summary,
            session_id="default_session",
        )
    except Exception as e:
        return {"status": "error", "message": f"Execution error creating escalation ticket: {str(e)}", "ticket_id": None}


# Groq / OpenAI Tool Schema Definitions - 5 Tools
TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_exam_schedule",
            "description": "Search the exam schedule dataset by student ID, course code, or subject. Returns exam date, start time, end time, room, and building.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "string", "description": "The student ID if known (e.g., 'S1001')."},
                    "course_code": {"type": "string", "description": "The course code (e.g., 'JAVA101', 'CS202', 'MATH301')."},
                    "subject": {"type": "string", "description": "The subject name (e.g., 'Java Programming', 'Data Structures')."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_details",
            "description": "Retrieve official course details including department, instructor, credit hours, and prerequisites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_code": {"type": "string", "description": "The course code (e.g., 'JAVA101', 'CS301')."},
                    "subject": {"type": "string", "description": "The subject or course name (e.g., 'Database Management Systems')."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_exam_rules",
            "description": "Search the official examination handbook for rules on reporting time, calculator usage, hall ticket eligibility, attendance, mobile phones, or cheating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The rule category or search keyword (e.g., 'reporting time', 'calculator policy', '75% attendance')."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_academic_docs",
            "description": "Semantic RAG search over college documents, course syllabi (DBMS, Units, topics), academic calendar, fee guidelines, and campus policies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic, unit name, or academic subject to search in college documents (e.g., 'DBMS syllabus Unit 3', 'midterm calendar dates', 'fee payment deadline')."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_escalation_ticket",
            "description": "Create an official human escalation ticket when evidence is conflicting/insufficient, a special financial waiver is needed, or the student explicitly asks to speak to human staff.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Detailed explanation of why human escalation is required."},
                    "student_question": {"type": "string", "description": "The original student question requiring escalation."},
                    "evidence_summary": {"type": "string", "description": "Summary of evidence gathered so far."},
                },
                "required": ["reason"],
            },
        },
    },
]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Safely dispatches tool execution against strict allowlist."""
    if tool_name not in ALLOWED_TOOLS:
        return {
            "status": "error",
            "message": f"Unauthorized tool invocation: '{tool_name}'. Allowed tools are {ALLOWED_TOOLS}.",
        }

    if not isinstance(arguments, dict):
        return {
            "status": "error",
            "message": f"Invalid arguments format for tool '{tool_name}': expected JSON object/dict.",
        }

    if tool_name == "get_exam_schedule":
        return get_exam_schedule(
            student_id=arguments.get("student_id"),
            course_code=arguments.get("course_code"),
            subject=arguments.get("subject"),
        )
    elif tool_name == "get_course_details":
        return get_course_details(
            course_code=arguments.get("course_code"),
            subject=arguments.get("subject"),
        )
    elif tool_name == "search_exam_rules":
        return search_exam_rules(query=arguments.get("query", ""))
    elif tool_name == "search_academic_docs":
        return search_academic_docs(query=arguments.get("query", ""))
    elif tool_name == "create_escalation_ticket":
        return create_escalation_ticket(
            reason=arguments.get("reason", ""),
            student_question=arguments.get("student_question"),
            evidence_summary=arguments.get("evidence_summary"),
        )

    return {"status": "error", "message": "Unknown tool routing error."}
