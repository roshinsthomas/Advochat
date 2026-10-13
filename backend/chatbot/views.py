import logging
from functools import lru_cache
from threading import Lock

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SearchRequestSerializer, ChatRequestSerializer
from .services.conversation_service import ConversationService
from .services.section_lookup import extract_section_numbers

logger = logging.getLogger(__name__)
search_lock = Lock()


@lru_cache(maxsize=1)
def get_search_service():
    # Load the models only when search is first requested.
    from .services.semantic_search import SemanticSearchService

    return SemanticSearchService()


@lru_cache(maxsize=1)
def get_query_tokenizer():
    from .services.token_chunker import TokenChunker

    return TokenChunker().tokenizer


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "OK"})


class SearchView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        limit = serializer.validated_data["limit"]

        try:
            # Serialize model access for this local CPU-based service.
            with search_lock:
                tokenizer = get_query_tokenizer()
                token_count = len(tokenizer.encode(query).ids)

                if token_count > 256:
                    raise serializers.ValidationError({
                        "query": (
                            "Your question is too long. "
                            "Please shorten it to fit 256 tokens."
                        )
                    })

                results = get_search_service().search(
                    query=query,
                    limit=limit,
                )

        except serializers.ValidationError:
            raise

        except Exception:
            logger.exception("Semantic search failed.")

            return Response(
                {"detail": "Search is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "query": query,
            "count": len(results),
            "source_scope": "historical_development_sample",
            "results": results,
        })

@lru_cache(maxsize=1)
def get_answer_service():
    from .services.answer_service import AnswerService

    return AnswerService()

@lru_cache(maxsize=1)
def get_context_service():
    from .services.context_service import ContextService

    return ContextService()

class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        limit = serializer.validated_data["limit"]
        conversation_id = serializer.validated_data.get(
            "conversation_id"
        )

        history = []

        # Load context only after verifying conversation ownership.
        if conversation_id:
            conversation = ConversationService.get_owned(
                request.user,
                conversation_id,
            )
            history = ConversationService.get_recent_messages(
                conversation
            )

        try:
            with search_lock:
                tokenizer = get_query_tokenizer()

                if len(tokenizer.encode(query).ids) > 256:
                    raise serializers.ValidationError({
                        "query": "Your question is too long. Please shorten it."
                    })

            # Only conversations with previous messages need rewriting.
            # Explicit section references take priority over older context.
            if extract_section_numbers(query):
                retrieval_query = query
            elif history:
                retrieval_query = get_context_service().rewrite(
                    query, history
                )
            else:
                retrieval_query = query

            with search_lock:
                if len(tokenizer.encode(retrieval_query).ids) > 256:
                    raise serializers.ValidationError({
                        "query": (
                            "The follow-up became too long for search. "
                            "Please ask a shorter, self-contained question."
                        )
                    })

                results = get_search_service().search(
                    query=retrieval_query,
                    limit=limit,
                )

            # Answer the original question with history and fresh sources.
            generated = get_answer_service().generate(
                query=query,
                results=results,
                history=history,
            )

        except serializers.ValidationError:
            raise

        except Exception as exc:
            logger.error(
                "Chat processing failed: %s",
                type(exc).__name__,
            )
            return Response(
                {
                    "detail": (
                        "Could not prepare an answer. "
                        "Check the API configuration, quota, and connection."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        conversation = ConversationService.save_exchange(
            user=request.user,
            conversation_id=conversation_id,
            query=query,
            generated=generated,
        )

        return Response({
            "conversation_id": str(conversation.id),
            "query": query,
            "retrieval_query": retrieval_query,
            **generated,
        })