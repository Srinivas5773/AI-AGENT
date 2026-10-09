import unittest
from backend.escalation import (
    create_escalation_ticket,
    get_all_tickets,
    update_ticket_status,
)


class TestEscalation(unittest.TestCase):

    def test_create_escalation_ticket(self):
        """Test persistent creation of escalation ticket in SQLite DB."""
        result = create_escalation_ticket(
            student_question="Need special financial aid fee waiver",
            reason="Special financial exemption request requires bursar authorization",
            evidence_summary="Student requested exemption under policy 3",
            session_id="test_escalation_session",
        )

        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["ticket_id"])
        self.assertTrue(result["ticket_id"].startswith("ESC-"))
        self.assertEqual(result["ticket"]["status"], "pending")

    def test_retrieve_all_tickets(self):
        """Test retrieving all escalation tickets from SQLite DB."""
        tickets = get_all_tickets()
        self.assertIsInstance(tickets, list)
        self.assertGreater(len(tickets), 0)

    def test_update_ticket_status(self):
        """Test authorized operator updating ticket status and resolution notes."""
        # Create ticket
        res = create_escalation_ticket(
            student_question="Conflicting attendance calculation",
            reason="Conflicting records in system",
        )
        ticket_id = res["ticket_id"]

        # Update ticket status to 'reviewed'
        update_res = update_ticket_status(
            ticket_id=ticket_id,
            new_status="reviewed",
            resolution_notes="Reviewed by Registrar. Verified attendance at 78%.",
        )
        self.assertEqual(update_res["status"], "success")
        self.assertEqual(update_res["new_status"], "reviewed")

        # Verify in DB query
        all_tickets = get_all_tickets(status_filter="reviewed")
        matching = [t for t in all_tickets if t["id"] == ticket_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["resolution_notes"], "Reviewed by Registrar. Verified attendance at 78%.")


if __name__ == "__main__":
    unittest.main()
