import unittest
from unittest.mock import patch

from app.services import email_service


class EmailServiceTests(unittest.TestCase):
    def test_send_email_rejects_missing_api_key(self):
        with patch.object(email_service, "BREVO_API_KEY", None):
            with self.assertRaises(RuntimeError) as ctx:
                email_service.send_email("test@example.com", "Subject", "<p>Hello</p>")

        self.assertEqual(str(ctx.exception), "BREVO_API_KEY is missing")

    def test_send_email_posts_expected_brevo_payload(self):
        class Response:
            status_code = 202
            text = ""

        with patch.object(email_service, "BREVO_API_KEY", "api-key"), patch.object(
            email_service.requests,
            "post",
            return_value=Response(),
        ) as mocked_post:
            email_service.send_email("test@example.com", "Subject", "<p>Hello</p>")

        mocked_post.assert_called_once()
        _url, kwargs = mocked_post.call_args
        self.assertEqual(_url[0], "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(kwargs["headers"]["api-key"], "api-key")
        self.assertEqual(kwargs["json"]["to"], [{"email": "test@example.com"}])
        self.assertEqual(kwargs["json"]["subject"], "Subject")
        self.assertEqual(kwargs["json"]["htmlContent"], "<p>Hello</p>")
        self.assertEqual(kwargs["timeout"], 15)

    def test_send_email_raises_on_brevo_error(self):
        class Response:
            status_code = 400
            text = "bad request"

        with patch.object(email_service, "BREVO_API_KEY", "api-key"), patch.object(
            email_service.requests,
            "post",
            return_value=Response(),
        ):
            with self.assertRaises(RuntimeError) as ctx:
                email_service.send_email("test@example.com", "Subject", "<p>Hello</p>")

        self.assertEqual(str(ctx.exception), "Brevo email failed: 400 bad request")

    def test_send_password_reset_email_delegates_to_send_email(self):
        with patch.object(email_service, "send_email") as mocked_send:
            email_service.send_password_reset_email("test@example.com", "https://reset")

        mocked_send.assert_called_once()
        kwargs = mocked_send.call_args.kwargs
        self.assertEqual(kwargs["to_email"], "test@example.com")
        self.assertIn("ForestForYou", kwargs["subject"])
        self.assertIn("https://reset", kwargs["html_content"])


if __name__ == "__main__":
    unittest.main()
