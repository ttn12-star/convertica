from django.test import SimpleTestCase
from src.feedback.tokens import create_feedback_token, resolve_feedback_token


class FeedbackTokenTests(SimpleTestCase):
    def test_roundtrip_request_id(self):
        token = create_feedback_token(request_id="req-abc")
        self.assertEqual(resolve_feedback_token(token), ("r", "req-abc"))

    def test_roundtrip_task_id(self):
        token = create_feedback_token(task_id="task-xyz")
        self.assertEqual(resolve_feedback_token(token), ("t", "task-xyz"))

    def test_tampered_token_rejected(self):
        token = create_feedback_token(request_id="req-abc")
        self.assertIsNone(resolve_feedback_token(token + "x"))

    def test_garbage_rejected(self):
        self.assertIsNone(resolve_feedback_token("not-a-token"))
        self.assertIsNone(resolve_feedback_token(""))

    def test_requires_an_identifier(self):
        with self.assertRaises(ValueError):
            create_feedback_token()
