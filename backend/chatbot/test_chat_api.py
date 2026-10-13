from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APISimpleTestCase


class ChatAPITests(APISimpleTestCase):
    def test_anonymous_request_is_rejected(self):
        response = self.client.post(
            reverse("chatbot:chat"),
            {"query": "Someone took my phone."},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_authenticated_chat_saves_exchange(self):
        # Unsaved user is enough for this mocked endpoint test.
        user = get_user_model()(id=1, username="testuser")
        self.client.force_authenticate(user=user)

        passages = [{"section_number": "378"}]
        generated = {
            "answer": "Sample explanation [S1].",
            "sources": [{"id": "S1", "section_number": "378"}],
            "source_scope": "historical_development_sample",
        }
        conversation_id = uuid4()

        with (
            patch("chatbot.views.get_query_tokenizer") as tokenizer,
            patch("chatbot.views.get_search_service") as search,
            patch("chatbot.views.get_answer_service") as answer,
            patch(
                "chatbot.views.ConversationService.save_exchange"
            ) as save,
        ):
            tokenizer.return_value.encode.return_value.ids = [1, 2]
            search.return_value.search.return_value = passages
            answer.return_value.generate.return_value = generated
            save.return_value = SimpleNamespace(id=conversation_id)

            response = self.client.post(
                reverse("chatbot:chat"),
                {"query": "Someone took my phone.", "limit": 3},
                format="json",
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.data["conversation_id"],
                str(conversation_id),
            )
            save.assert_called_once_with(
                user=user,
                conversation_id=None,
                query="Someone took my phone.",
                generated=generated,
            )
    def test_followup_uses_history_for_search_and_answer(self):
        user = get_user_model()(id=1, username="testuser")
        self.client.force_authenticate(user=user)

        conversation_id = uuid4()
        conversation = SimpleNamespace(id=conversation_id)
        history = [
            {"role": "user", "content": "Someone took my phone."},
            {"role": "assistant", "content": "We discussed theft."},
        ]
        generated = {
            "answer": "A sample answer.",
            "sources": [],
            "source_scope": "historical_development_sample",
        }

        with (
            patch("chatbot.views.get_query_tokenizer") as tokenizer,
            patch("chatbot.views.get_context_service") as context,
            patch("chatbot.views.get_search_service") as search,
            patch("chatbot.views.get_answer_service") as answer,
            patch(
                "chatbot.views.ConversationService.get_owned"
            ) as owned,
            patch(
                "chatbot.views.ConversationService.get_recent_messages"
            ) as recent,
            patch(
                "chatbot.views.ConversationService.save_exchange"
            ) as save,
        ):
            tokenizer.return_value.encode.return_value.ids = [1, 2]
            owned.return_value = conversation
            recent.return_value = history
            context.return_value.rewrite.return_value = (
                "What is the punishment for theft of a phone?"
            )
            search.return_value.search.return_value = []
            answer.return_value.generate.return_value = generated
            save.return_value = conversation

            response = self.client.post(
                reverse("chatbot:chat"),
                {
                    "query": "What is its punishment?",
                    "conversation_id": str(conversation_id),
                    "limit": 3,
                },
                format="json",
            )

            self.assertEqual(response.status_code, 200)

            owned.assert_called_once_with(user, conversation_id)
            recent.assert_called_once_with(conversation)

            context.return_value.rewrite.assert_called_once_with(
                "What is its punishment?", history
            )
            search.return_value.search.assert_called_once_with(
                query="What is the punishment for theft of a phone?",
                limit=3,
            )
            answer.return_value.generate.assert_called_once_with(
                query="What is its punishment?",
                results=[],
                history=history,
            )