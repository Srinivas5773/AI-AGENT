import json
import logging
import re
from typing import Any, Dict, List, Optional
from groq import Groq

from backend.config import GROQ_API_KEY, GROQ_MODEL, MAX_ITERATIONS
from backend.tools import TOOLS_SCHEMA, ALLOWED_TOOLS, execute_tool
from backend.memory import memory_manager
from backend.intent import classify_conversational_intent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are AI Student Academic Support Agent (NEC Campus Copilot AI), an intelligent academic assistant for Narasaraopeta Engineering College (Autonomous).

ANSWERING & RETRIEVAL GUIDELINES FOR ALL B.TECH BRANCHES:
1. OFFICIAL NEC RECORDS & SYLLABI: For questions regarding official college schedules, exam dates, room numbers, attendance rules, or NEC B.Tech course syllabi across ALL engineering branches (CSE, AI/ML, Data Science, ECE, EEE, Mechanical, Civil Engineering, MCA, MBA), use the available tools (get_exam_schedule, get_course_details, search_exam_rules, search_academic_docs, create_escalation_ticket) and provide explicit source citations (e.g. "[nec_btech_cse_aiml_ds_syllabi.txt, Page 1]" or "[nec_btech_ece_eee_syllabi.txt, Page 1]").
2. UNIVERSAL B.TECH & TECHNICAL KNOWLEDGE: If a student asks any general programming, computer science, electronics, electrical, mechanical, civil engineering, math, or physics question (e.g. Java OOP, Data Structures, Algorithms, Operating Systems, Computer Networks, Signals & Systems, VLSI, Thermodynamics, Fluid Mechanics, Strength of Materials, Python, C++), answer comprehensively, accurately, and helpfully using general academic engineering knowledge. Never decline general technical or engineering queries.
3. CONVERSATION MEMORY: Use conversation history to resolve follow-up questions (e.g. "What about Unit 3?" following a query about any subject).
4. HUMAN ESCALATION CRITERIA — ONLY call `create_escalation_ticket` when:
   - The student explicitly asks to speak to a human staff member, advisor, or representative.
   - The student requests a formal administrative waiver or special financial/medical exemption.
   - Critical conflicting records exist that require human administrative resolution.
   DO NOT create escalation tickets for greetings, thanks, or standard technical/academic queries.

REQUIRED ANSWER FORMAT:
### Answer & Evidence
[Grounded summary of retrieved information or comprehensive engineering explanation with citations if retrieved]

### Exam / Course Details (if applicable)
- **Subject / Course Code**: [Retrieved value]
- **Details**: [Retrieved values]

### Relevant Rules & Guidelines (if applicable)
- **Rule Summary**: [Retrieved rule text with citation]

### Human Escalation Status (if ticket created)
- **Ticket ID**: [Retrieved ticket ID e.g., ESC-1001]
- **Status**: Pending Human Review
- **Reason**: [Explanation of human escalation]
"""


def resolve_followup_query(question: str, history: List[Dict[str, str]]) -> str:
    """Combines current question with past academic topic if it's a follow-up query."""
    q_lower = question.lower().strip()
    followup_indicators = ["unit", "topic", "topics", "that", "it", "chapter", "section", "what about", "tell me more"]

    if history and any(ind in q_lower for ind in followup_indicators):
        user_msgs = [m["content"] for m in history if m["role"] == "user"]
        if user_msgs:
            last_context = user_msgs[-1]
            unit_match = re.search(r"unit\s*\d+", q_lower)
            if unit_match:
                u_str = unit_match.group(0).upper()
                return f"{u_str} Normalization {question} ({last_context})"
            return f"{question} ({last_context})"
    return question


def run_agent_fallback_mock(question: str, session_id: str = "default_session") -> Dict[str, Any]:
    """Fallback agent loop when GROQ API key is missing or offline."""
    logger.warning("Running fallback agent loop with local tool execution.")

    # 1. Check Conversational Intent First
    intent_res = classify_conversational_intent(question)
    if intent_res:
        memory_manager.add_message(session_id, "user", question)
        memory_manager.add_message(session_id, "assistant", intent_res["answer"])
        return intent_res

    history = memory_manager.get_history(session_id)
    combined_query = resolve_followup_query(question, history)
    combined_lower = combined_query.lower()

    tools_used = []
    tool_results = []
    citations = []

    # Determine tool triggers
    needs_escalation = any(k in combined_lower for k in ["escalate", "human staff", "speak to staff", "representative", "special exemption", "financial aid waiver", "bursar exemption"])
    needs_schedule = any(k in combined_lower for k in ["java exam", "cs202 exam", "math301 exam", "s1001 schedule", "my java exam", "my exam schedule"])
    needs_course = any(k in combined_lower for k in ["course details", "prerequisite", "instructor", "credit", "department"])
    needs_rules = any(k in combined_lower for k in ["reporting time", "reporting-time", "calculator policy", "attendance rule", "75%", "late entry", "phone rule"])
    needs_rag = True  # Always search RAG for document evidence

    if needs_rag:
        tools_used.append("search_academic_docs")
        res = execute_tool("search_academic_docs", {"query": combined_query})
        tool_results.append(("search_academic_docs", res))

    if needs_schedule:
        tools_used.append("get_exam_schedule")
        student_id = "S1001" if "s1001" in combined_lower else None
        course_code = "JAVA101" if "java" in combined_lower else ("CS202" if "cs202" in combined_lower else ("MATH301" if "math301" in combined_lower else None))
        res = execute_tool("get_exam_schedule", {"student_id": student_id, "course_code": course_code})
        tool_results.append(("get_exam_schedule", res))

    if needs_course:
        tools_used.append("get_course_details")
        course_code = "JAVA101" if "java" in combined_lower else ("CS202" if "cs202" in combined_lower else ("CS301" if "dbms" in combined_lower or "cs301" in combined_lower else None))
        res = execute_tool("get_course_details", {"course_code": course_code})
        tool_results.append(("get_course_details", res))

    if needs_rules:
        tools_used.append("search_exam_rules")
        query = "reporting time" if "reporting" in combined_lower else ("calculator" if "calculator" in combined_lower else ("attendance" if "attendance" in combined_lower else "rules"))
        res = execute_tool("search_exam_rules", {"query": query})
        tool_results.append(("search_exam_rules", res))

    if needs_escalation:
        tools_used.append("create_escalation_ticket")
        res = execute_tool("create_escalation_ticket", {"reason": "Student requested special administrative exemption or human representative", "student_question": question})
        tool_results.append(("create_escalation_ticket", res))

    # Synthesize grounded answer
    answer_parts = []
    rag_data = next((r for name, r in tool_results if name == "search_academic_docs"), None)
    schedule_data = next((r for name, r in tool_results if name == "get_exam_schedule"), None)
    rules_data = next((r for name, r in tool_results if name == "search_exam_rules"), None)
    escalation_data = next((r for name, r in tool_results if name == "create_escalation_ticket"), None)

    answer_parts.append("### Answer & Evidence")
    if rag_data and rag_data.get("results"):
        for r in rag_data["results"]:
            citations.append(r["source_citation"])
            answer_parts.append(f"- {r['text']} **Source: {r['source_citation']}**")
    else:
        answer_parts.append(f"- The requested information for '{question}' could not be verified in official college records.")

    if schedule_data and schedule_data.get("records"):
        rec = schedule_data["records"][0]
        answer_parts.append("\n### Exam Details")
        answer_parts.append(f"- **Student**: {rec.get('student_name', 'N/A')} ({rec.get('student_id', 'N/A')})")
        answer_parts.append(f"- **Exam Date & Time**: {rec.get('exam_date')} ({rec.get('start_time')} - {rec.get('end_time')})")
        answer_parts.append(f"- **Room**: {rec.get('room')} [{rec.get('building')}]")

    if rules_data and rules_data.get("rules"):
        rule = rules_data["rules"][0]
        answer_parts.append("\n### Relevant Rules & Guidelines")
        answer_parts.append(f"- {rule.get('rule_text')} **Source: [synthetic_exam_rules.txt, Section {rule.get('section_index')}]**")

    if escalation_data and escalation_data.get("ticket_id"):
        answer_parts.append("\n### Human Escalation Status")
        answer_parts.append(f"- **Ticket ID**: `{escalation_data['ticket_id']}`")
        answer_parts.append(f"- **Status**: Pending Human Review")
        answer_parts.append(f"- **Reason**: {escalation_data.get('message')}")

    final_answer = "\n".join(answer_parts)

    memory_manager.add_message(session_id, "user", question)
    memory_manager.add_message(session_id, "assistant", final_answer)

    return {
        "answer": final_answer,
        "tools_used": list(set(tools_used)),
        "citations": list(set(citations)),
        "iterations": 1,
        "success": True,
        "mode": "fallback_mock",
    }


def run_agent(question: str, session_id: str = "default_session") -> Dict[str, Any]:
    """Runs the Groq Agentic LLM tool-calling loop with RAG, Memory, Intent Classification, and Escalation."""
    # 1. Check Conversational Intent First
    intent_res = classify_conversational_intent(question)
    if intent_res:
        memory_manager.add_message(session_id, "user", question)
        memory_manager.add_message(session_id, "assistant", intent_res["answer"])
        return intent_res

    if not GROQ_API_KEY or GROQ_API_KEY.strip() in ["your_actual_groq_api_key", ""]:
        return run_agent_fallback_mock(question, session_id=session_id)

    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return run_agent_fallback_mock(question, session_id=session_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Load session history for conversation memory
    history = memory_manager.get_history(session_id)
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current question (resolving follow-up if applicable)
    combined_question = resolve_followup_query(question, history)
    messages.append({"role": "user", "content": combined_question})

    tools_used: List[str] = []
    citations: List[str] = []
    executed_escalation = False
    iterations = 0

    while iterations < MAX_ITERATIONS:
        iterations += 1
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.1,
            )
        except Exception as api_err:
            logger.error(f"Groq API Error on iteration {iterations}: {api_err}")
            return run_agent_fallback_mock(question, session_id=session_id)

        choice = response.choices[0]
        assistant_msg = choice.message

        assistant_dict = {"role": "assistant"}
        if assistant_msg.content:
            assistant_dict["content"] = assistant_msg.content
        if assistant_msg.tool_calls:
            assistant_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_msg.tool_calls
            ]

        messages.append(assistant_dict)

        # Final answer reached
        if not assistant_msg.tool_calls:
            final_text = assistant_msg.content or "No response generated."

            # Save to conversation memory
            memory_manager.add_message(session_id, "user", question)
            memory_manager.add_message(session_id, "assistant", final_text)

            return {
                "answer": final_text,
                "tools_used": list(set(tools_used)),
                "citations": list(set(citations)),
                "iterations": iterations,
                "success": True,
                "mode": "groq_api",
            }

        # Process tool calls
        for tool_call in assistant_msg.tool_calls:
            func_name = tool_call.function.name
            func_args_str = tool_call.function.arguments or "{}"
            tool_call_id = tool_call.id

            # Prevent duplicate escalation ticket creation in same turn
            if func_name == "create_escalation_ticket":
                if executed_escalation:
                    tool_result = {"status": "skipped", "message": "Escalation ticket already created for this query."}
                    messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": func_name, "content": json.dumps(tool_result)})
                    continue
                executed_escalation = True

            tools_used.append(func_name)

            try:
                func_args = json.loads(func_args_str)
            except Exception:
                func_args = {}

            # Execute tool safely
            tool_result = execute_tool(func_name, func_args)

            # Capture citations if RAG tool
            if func_name == "search_academic_docs" and isinstance(tool_result, dict):
                for r in tool_result.get("results", []):
                    if "source_citation" in r:
                        citations.append(r["source_citation"])

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": func_name,
                    "content": json.dumps(tool_result),
                }
            )

    # Iteration limit fallback
    return {
        "answer": f"Agent reached maximum safety iteration limit ({MAX_ITERATIONS}).",
        "tools_used": list(set(tools_used)),
        "citations": list(set(citations)),
        "iterations": iterations,
        "success": False,
        "error": "Max iterations reached",
    }
