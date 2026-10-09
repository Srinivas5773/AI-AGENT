import unittest
from unittest.mock import patch
from backend.tools import (
    get_exam_schedule,
    get_course_details,
    search_exam_rules,
    search_academic_docs,
    create_escalation_ticket,
    execute_tool,
)


class TestTools(unittest.TestCase):

    def test_valid_exam_schedule_lookup(self):
        """Tool 1: Valid exam schedule lookup by student_id or course_code."""
        result = get_exam_schedule(student_id="S1001")
        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(result["count"], 1)
        self.assertEqual(result["records"][0]["student_id"], "S1001")

    def test_valid_course_details_lookup(self):
        """Tool 2: Valid course details lookup by course_code."""
        result = get_course_details(course_code="JAVA101")
        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(result["count"], 1)
        self.assertEqual(result["courses"][0]["course_code"], "JAVA101")

    def test_relevant_rule_search(self):
        """Tool 3: Relevant rule search by keyword."""
        result = search_exam_rules(query="reporting time")
        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(result["count"], 1)
        self.assertIn("rule", result["rules"][0]["rule_text"].lower())

    def test_search_academic_docs_rag(self):
        """Tool 4 (RAG): Search academic documents for syllabus/calendar topics."""
        result = search_academic_docs(query="DBMS syllabus Unit 3")
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["count"], 0)
        self.assertIn("source_citation", result["results"][0])

    def test_create_escalation_ticket_tool(self):
        """Tool 5 (Escalation): Create human escalation ticket."""
        result = create_escalation_ticket(
            reason="Special financial exemption request",
            student_question="How do I get a fee waiver?",
        )
        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["ticket_id"])
        self.assertTrue(result["ticket_id"].startswith("ESC-"))

    def test_unknown_subject(self):
        """Lookup for an unknown subject."""
        result = get_exam_schedule(subject="Quantum Astro-Cooking")
        self.assertEqual(result["status"], "no_results")
        self.assertEqual(result["count"], 0)

    def test_unknown_course_code(self):
        """Lookup for an unknown course code."""
        result = get_course_details(course_code="UNKNOWN999")
        self.assertEqual(result["status"], "no_results")
        self.assertEqual(result["count"], 0)

    def test_absent_rule_search(self):
        """Rule search for a rule absent from document."""
        result = search_exam_rules(query="skydive parachute scuba diving policy")
        self.assertEqual(result["status"], "no_results")
        self.assertEqual(result["count"], 0)

    def test_invalid_tool_request(self):
        """Unauthorized tool execution attempt."""
        result = execute_tool("execute_os_shell_command", {"command": "dir"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Unauthorized tool invocation", result["message"])

    def test_invalid_tool_argument_type(self):
        """Tool argument parsing/execution error."""
        result = execute_tool("get_exam_schedule", "not_a_dict")
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid arguments format", result["message"])


if __name__ == "__main__":
    unittest.main()
