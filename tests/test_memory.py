import unittest
from backend.memory import SessionMemoryManager


class TestMemory(unittest.TestCase):

    def setUp(self):
        self.memory = SessionMemoryManager()

    def test_add_and_retrieve_history(self):
        """Test adding messages and retrieving session history."""
        session_id = "test_session_101"
        self.memory.add_message(session_id, "user", "Explain my DBMS syllabus.")
        self.memory.add_message(session_id, "assistant", "DBMS covers relational algebra and normalization.")

        history = self.memory.get_history(session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "Explain my DBMS syllabus.")

    def test_session_isolation(self):
        """Test that different session IDs maintain separate isolated histories."""
        self.memory.add_message("session_A", "user", "Question for Session A")
        self.memory.add_message("session_B", "user", "Question for Session B")

        hist_A = self.memory.get_history("session_A")
        hist_B = self.memory.get_history("session_B")

        self.assertEqual(len(hist_A), 1)
        self.assertEqual(len(hist_B), 1)
        self.assertEqual(hist_A[0]["content"], "Question for Session A")
        self.assertEqual(hist_B[0]["content"], "Question for Session B")

    def test_clear_session(self):
        """Test clearing/resetting session memory."""
        session_id = "reset_test_session"
        self.memory.add_message(session_id, "user", "Message to reset")
        self.assertTrue(len(self.memory.get_history(session_id)) == 1)

        cleared = self.memory.clear_session(session_id)
        self.assertTrue(cleared)
        self.assertEqual(len(self.memory.get_history(session_id)), 0)


if __name__ == "__main__":
    unittest.main()
