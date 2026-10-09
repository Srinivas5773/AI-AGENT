import unittest
from fastapi.testclient import TestClient
from backend.main import app


class TestAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test GET /health status."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("rag_chunks_count", data)
        self.assertIn("escalation_tickets_count", data)

    def test_valid_chat_request(self):
        """Test POST /chat endpoint."""
        payload = {
            "question": "Explain my DBMS syllabus Unit 3 topics.",
            "session_id": "test_api_session_1",
        }
        response = self.client.post("/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("answer", data)
        self.assertIsInstance(data["tools_used"], list)

    def test_reset_session_endpoint(self):
        """Test POST /reset endpoint to clear session memory."""
        payload = {"session_id": "test_api_session_1"}
        response = self.client.post("/reset", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["session_id"], "test_api_session_1")

    def test_get_and_update_escalations(self):
        """Test GET /escalations and PATCH /escalations/{ticket_id} endpoints."""
        # Create ticket via chat or escalation DB
        chat_payload = {
            "question": "I want to speak to a human staff member for financial aid.",
            "session_id": "escalation_api_session",
        }
        self.client.post("/chat", json=chat_payload)

        # GET /escalations
        get_res = self.client.get("/escalations")
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertGreater(data["count"], 0)
        ticket_id = data["tickets"][0]["id"]

        # PATCH /escalations/{ticket_id}
        patch_res = self.client.patch(
            f"/escalations/{ticket_id}",
            json={"status": "resolved", "resolution_notes": "Financial aid approved by Bursar."},
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["new_status"], "resolved")

    def test_invalid_empty_chat_request(self):
        """Test POST /chat with empty question."""
        payload = {"question": "   "}
        response = self.client.post("/chat", json=payload)
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
