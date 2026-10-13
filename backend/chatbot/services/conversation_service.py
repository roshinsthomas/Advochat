from django.db import transaction
from django.shortcuts import get_object_or_404

from chatbot.models import Conversation, Message


class ConversationService:
    @staticmethod
    def get_owned(user, conversation_id):
        return get_object_or_404(
            Conversation,
            id=conversation_id,
            user=user,
        )

    @staticmethod
    @transaction.atomic
    def save_exchange(user, conversation_id, query, generated):
        if conversation_id:
            # Lock the row while saving the pair and updating its title.
            conversation = get_object_or_404(
                Conversation.objects.select_for_update(),
                id=conversation_id,
                user=user,
            )
        else:
            conversation = Conversation.objects.create(
                user=user,
                title=query[:120],
            )

        if conversation.title == "New conversation":
            conversation.title = query[:120]

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=query,
        )

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=generated["answer"],
            sources=generated["sources"],
        )

        conversation.save(update_fields=["title", "updated_at"])
        return conversation
    
    @staticmethod
    def get_recent_messages(conversation, limit=6):
        rows = list(
            conversation.messages
            .order_by("-created_at", "-id")
            .values("role", "content")[:limit]
        )

        # Fetch newest first, then restore chronological order.
        return [
            {
                "role": row["role"],
                "content": row["content"][:3000],
            }
            for row in reversed(rows)
        ]