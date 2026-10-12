from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APISimpleTestCase


class SearchAPITests(APISimpleTestCase):
    @patch("chatbot.views.get_search_service")
    @patch("chatbot.views.get_query_tokenizer")
    def test_valid_question_returns_results(
        self, mock_tokenizer, mock_service
    ):
        mock_tokenizer.return_value.encode.return_value.ids = [1, 2, 3]
        mock_service.return_value.search.return_value = [
            {"section_number": "378", "matched_chunk": "Sample passage"}
        ]

        response = self.client.post(
            reverse("chatbot:search"),
            {"query": "Someone took my phone.", "limit": 3},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["section_number"], "378"
        )
        mock_service.return_value.search.assert_called_once_with(
            query="Someone took my phone.",
            limit=3,
        )

    @patch("chatbot.views.get_search_service")
    def test_blank_question_is_rejected(self, mock_service):
        response = self.client.post(
            reverse("chatbot:search"),
            {"query": "   "},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        mock_service.assert_not_called()

    @patch("chatbot.views.get_search_service")
    @patch("chatbot.views.get_query_tokenizer")
    def test_overlong_question_is_rejected(
        self, mock_tokenizer, mock_service
    ):
        mock_tokenizer.return_value.encode.return_value.ids = [1] * 257

        response = self.client.post(
            reverse("chatbot:search"),
            {"query": "A question exceeding the token limit."},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        mock_service.assert_not_called()