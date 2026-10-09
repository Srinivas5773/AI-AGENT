import unittest
from backend.agent import run_agent
from backend.memory import memory_manager
from backend.escalation import get_all_tickets


class TestRegressionFixes(unittest.TestCase):

    def setUp(self):
        self.session_id = "test_regression_session_99"
        memory_manager.clear_session(self.session_id)

    def test_1_greeting_returns_friendly_response_no_tools(self):
        """Fix Requirement 1: 'hi' returns a friendly greeting with no tool execution."""
        res = run_agent("hi", session_id=self.session_id)
        self.assertTrue(res["success"])
        self.assertEqual(res["tools_used"], [])
        self.assertEqual(len(res.get("citations", [])), 0)
        self.assertIn("Hello!", res["answer"])
        self.assertIn("Student Academic Support", res["answer"])

    def test_2_thank_you_no_escalation_ticket(self):
        """Fix Requirement 2: 'thank you' does not create an escalation ticket or run tools."""
        tickets_before = len(get_all_tickets())
        res = run_agent("thank you", session_id=self.session_id)
        tickets_after = len(get_all_tickets())

        self.assertTrue(res["success"])
        self.assertEqual(res["tools_used"], [])
        self.assertEqual(tickets_after, tickets_before)
        self.assertIn("welcome", res["answer"].lower())

    def test_3_academic_question_triggers_retrieval(self):
        """Fix Requirement 3: Academic question triggers appropriate schedule/RAG tool."""
        res = run_agent("When is my Java exam?", session_id=self.session_id)
        self.assertTrue(res["success"])
        self.assertIn("get_exam_schedule", res["tools_used"])
        self.assertIn("2026-10-15", res["answer"])

    def test_4_multi_step_academic_question(self):
        """Fix Requirement 4: Multi-step academic question uses multiple necessary tools."""
        res = run_agent("When is my Java exam, and what reporting time rule applies?", session_id=self.session_id)
        self.assertTrue(res["success"])
        self.assertIn("get_exam_schedule", res["tools_used"])
        self.assertIn("search_exam_rules", res["tools_used"])

    def test_5_followup_preserves_preceding_context(self):
        """Fix Requirement 5: 'What about Unit 3?' preserves preceding DBMS Unit 3 context."""
        # Step 1: Initial syllabus question
        res1 = run_agent("Explain my DBMS syllabus.", session_id=self.session_id)
        self.assertTrue(res1["success"])

        # Step 2: Follow-up question
        res2 = run_agent("What about Unit 3?", session_id=self.session_id)
        self.assertTrue(res2["success"])
        self.assertIn("search_academic_docs", res2["tools_used"])
        self.assertIn("NORMALIZATION", res2["answer"].upper())

    def test_6_explicit_human_support_request_creates_one_ticket(self):
        """Fix Requirement 6: Explicit human request creates exactly one real escalation ticket."""
        tickets_before = len(get_all_tickets())
        res = run_agent("I want to speak to a human staff member for financial aid.", session_id=self.session_id)
        tickets_after = len(get_all_tickets())

        self.assertTrue(res["success"])
        self.assertIn("create_escalation_ticket", res["tools_used"])
        self.assertEqual(tickets_after, tickets_before + 1)
        self.assertIn("ESC-", res["answer"])

    def test_7_missing_evidence_does_not_fabricate(self):
        """Fix Requirement 7: Missing evidence returns unverified message without inventing facts."""
        res = run_agent("When is the Quantum Astro-Cooking 909 exam?", session_id=self.session_id)
        self.assertTrue(res["success"])
        self.assertIn("could not be verified", res["answer"].lower())
        self.assertNotIn("2026-12-25", res["answer"])


if __name__ == "__main__":
    unittest.main()
