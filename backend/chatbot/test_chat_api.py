from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APISimpleTestCase


class ChatAPITests(APISimpleTestCase):
    @patch("chatbot.views.get_answer_service")
    @patch("chatbot.views.get_search_service")
    @patch("chatbot.views.get_query_tokenizer")
    def test_chat_returns_generated_answer(
        self, mock_tokenizer, mock_search, mock_answer
    ):
        mock_tokenizer.return_value.encode.return_value.ids = [1, 2]

        passages = [{"section_number": "378"}]
        mock_search.return_value.search.return_value = passages

        mock_answer.return_value.generate.return_value = {
            "answer": "An explanation based on the sample [S1].",
            "sources": [{"id": "S1", "section_number": "378"}],
            "source_scope": "historical_development_sample",
        }

        response = self.client.post(
            reverse("chatbot:chat"),
            {"query": "Someone took my phone.", "limit": 3},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sources"][0]["id"], "S1")
        mock_answer.return_value.generate.assert_called_once_with(
            query="Someone took my phone.",
            results=passages,
        )