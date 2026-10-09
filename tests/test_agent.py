import unittest
from unittest.mock import MagicMock, patch
from backend.agent import run_agent, run_agent_fallback_mock


class TestAgent(unittest.TestCase):

    def test_fallback_mock_multi_step_workflow(self):
        """Combined RAG + Schedule + Rules multi-step query in fallback mode."""
        question = "When is my Java exam, explain my DBMS syllabus, and what reporting time rule applies?"
        result = run_agent_fallback_mock(question, session_id="test_agent_session")
        self.assertTrue(result["success"])
        self.assertIn("get_exam_schedule", result["tools_used"])
        self.assertIn("search_academic_docs", result["tools_used"])
        self.assertIn("search_exam_rules", result["tools_used"])

    def test_fallback_mock_escalation_workflow(self):
        """Human escalation trigger in fallback mode."""
        question = "I want to speak to a human staff member for a special fee exemption."
        result = run_agent_fallback_mock(question, session_id="test_agent_session")
        self.assertTrue(result["success"])
        self.assertIn("create_escalation_ticket", result["tools_used"])
        self.assertIn("Human Escalation Status", result["answer"])

    @patch("backend.agent.Groq")
    def test_mocked_groq_api_multi_step_loop(self, mock_groq_cls):
        """Mocked Groq multi-turn tool calling with RAG and citations."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_rag_1"
        mock_tool_call.function.name = "search_academic_docs"
        mock_tool_call.function.arguments = '{"query": "DBMS Unit 3"}'

        msg_turn_1 = MagicMock()
        msg_turn_1.content = None
        msg_turn_1.tool_calls = [mock_tool_call]

        choice_1 = MagicMock()
        choice_1.message = msg_turn_1
        response_1 = MagicMock()
        response_1.choices = [choice_1]

        msg_turn_2 = MagicMock()
        msg_turn_2.content = "### Answer & Evidence\nDBMS Unit 3 covers Normalization [nec_syllabi_r20_r23.txt, Page 1]."
        msg_turn_2.tool_calls = None

        choice_2 = MagicMock()
        choice_2.message = msg_turn_2
        response_2 = MagicMock()
        response_2.choices = [choice_2]

        mock_client.chat.completions.create.side_effect = [response_1, response_2]

        with patch("backend.agent.GROQ_API_KEY", "valid_mock_groq_key"):
            result = run_agent("Explain Unit 3 of DBMS syllabus.", session_id="mock_session")

        self.assertTrue(result["success"])
        self.assertEqual(result["iterations"], 2)
        self.assertIn("search_academic_docs", result["tools_used"])
        self.assertIn("nec_syllabi_r20_r23.txt", result["answer"])


if __name__ == "__main__":
    unittest.main()
