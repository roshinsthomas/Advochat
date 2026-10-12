import logging
from functools import lru_cache
from threading import Lock

from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SearchRequestSerializer


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


class ChatView(SearchView):
    def post(self, request):
        # Reuse the search endpoint's validation and retrieval.
        search_response = super().post(request)

        if search_response.status_code != status.HTTP_200_OK:
            return search_response

        query = search_response.data["query"]
        results = search_response.data["results"]

        try:
            generated = get_answer_service().generate(
                query=query,
                results=results,
            )

        except Exception as exc:
            # Log the error type without exposing credentials or prompts.
            logger.error(
                "Answer generation failed: %s",
                type(exc).__name__,
            )

            return Response(
                {
                    "detail": (
                        "Answer generation is unavailable. "
                        "Check the API configuration, quota, and connection."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "query": query,
            **generated,
        })