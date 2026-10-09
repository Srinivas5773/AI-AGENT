import unittest
from backend.study_mode import generate_study_mode_content, generate_study_mode_fallback


class TestStudyMode(unittest.TestCase):

    def test_explain_simply_action(self):
        """Test 'Explain Simply' study mode action."""
        res = generate_study_mode_content("explain_simply", "Database Normalization")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["action"], "explain_simply")
        self.assertIn("content", res)

    def test_practical_example_action(self):
        """Test 'Practical Example' study mode action."""
        res = generate_study_mode_content("practical_example", "ACID Properties in Transactions")
        self.assertEqual(res["status"], "success")
        self.assertIn("content", res)

    def test_practice_questions_action_and_label(self):
        """Test 'Generate Practice Questions' action and official disclaimer label."""
        res = generate_study_mode_content("practice_questions", "DBMS Unit 3")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["is_practice_label"], "Practice Questions - Not Official Exam Questions")
        self.assertIn("Practice Questions", res["content"])

    def test_flashcards_action(self):
        """Test 'Create Flashcards' study mode action."""
        res = generate_study_mode_content("flashcards", "BCNF Normal Form")
        self.assertEqual(res["status"], "success")
        self.assertIn("content", res)

    def test_summarize_notes_action(self):
        """Test 'Summarize Notes' study mode action."""
        res = generate_study_mode_content("summarize_notes", "DBMS Functional Dependencies")
        self.assertEqual(res["status"], "success")
        self.assertIn("content", res)


if __name__ == "__main__":
    unittest.main()
