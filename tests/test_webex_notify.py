import contextlib
import io
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import webex_notify as webex


class WebexNotificationTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "WEBEX_BOT_TOKEN": "fake-test-token",
            "WEBEX_ROOM_ID": "fake-test-room",
            "JOB_NAME": "Integrated-CI-CD-pipeline",
            "BUILD_NUMBER": "7",
            "GIT_COMMIT": "0123456789abcdef",
            "GIT_BRANCH": "origin/main",
            "BUILD_URL": "http://localhost:8080/job/example/7/",
        }

    def response(self, body, status=200):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = status
        response.read.return_value = json.dumps(body).encode("utf-8")
        response.headers = {}
        return response

    def test_message_contains_build_identity(self):
        message = webex.build_message("SUCCESS", self.env)
        for value in ("SUCCESS", "#7", "0123456789abcdef", "origin/main", "http://localhost:8080/job/example/7/"):
            self.assertIn(value, message)
        self.assertNotIn(self.env["WEBEX_BOT_TOKEN"], message)

    def test_failure_message(self):
        self.assertIn("FAILURE", webex.build_message("FAILURE", self.env))

    @patch.object(webex, "urlopen")
    def test_posts_correct_room_and_authorization(self, opener):
        opener.return_value = self.response({"id": "created-message"}, status=201)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            webex.send_notification("SUCCESS", self.env)
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, "https://webexapis.com/v1/messages")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer fake-test-token")
        self.assertEqual(json.loads(request.data)["roomId"], "fake-test-room")
        self.assertEqual(opener.call_args.kwargs["timeout"], 30)
        self.assertIn("sent successfully", output.getvalue())
        self.assertNotIn("fake-test-token", output.getvalue())

    @patch.object(webex, "urlopen")
    def test_missing_credentials_never_sends(self, opener):
        with self.assertRaises(webex.WebexError):
            webex.send_notification("SUCCESS", {})
        opener.assert_not_called()

    @patch.object(webex, "urlopen")
    def test_http_error_is_actionable_and_redacted(self, opener):
        opener.side_effect = HTTPError(webex.API + "messages", 401, "private text", {}, io.BytesIO(b"sensitive body"))
        with self.assertRaisesRegex(webex.WebexError, "401") as caught:
            webex.send_notification("FAILURE", self.env)
        self.assertNotIn("private text", str(caught.exception))
        self.assertNotIn("sensitive body", str(caught.exception))

    @patch.object(webex, "urlopen", side_effect=URLError("connection failed"))
    def test_network_failure_is_reported(self, opener):
        with self.assertRaisesRegex(webex.WebexError, "Cannot reach Webex"):
            webex.send_notification("SUCCESS", self.env)

    @patch.object(webex, "urlopen")
    def test_unconfirmed_message_is_failure(self, opener):
        opener.return_value = self.response({})
        with self.assertRaisesRegex(webex.WebexError, "message ID"):
            webex.send_notification("SUCCESS", self.env)

    @patch.object(webex, "urlopen")
    def test_unexpected_api_url_never_receives_token(self, opener):
        with self.assertRaises(webex.WebexError):
            webex.request_json("https://example.invalid/v1/rooms", "fake-test-token")
        opener.assert_not_called()

    @patch.object(webex, "request_json")
    def test_lists_rooms_across_pages(self, request):
        request.side_effect = [
            ({"items": [{"id": "one", "title": "First", "type": "group"}]}, {"Link": '<https://webexapis.com/v1/rooms?cursor=2>; rel="next"'}),
            ({"items": [{"id": "two", "title": "Lab", "type": "group"}]}, {}),
        ]
        with contextlib.redirect_stdout(io.StringIO()) as output:
            webex.list_rooms("fake-test-token")
        self.assertIn("Room ID: one", output.getvalue())
        self.assertIn("Room ID: two", output.getvalue())
        self.assertEqual(request.call_count, 2)

    @patch.object(webex, "request_json", return_value=({"items": []}, {}))
    def test_empty_room_list_explains_membership(self, request):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            webex.list_rooms("fake-test-token")
        self.assertIn("Add the bot", output.getvalue())


if __name__ == "__main__":
    unittest.main()
