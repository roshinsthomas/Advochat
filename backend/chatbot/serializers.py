from rest_framework import serializers


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        max_length=1000,
        allow_blank=False,
        trim_whitespace=True,
    )
    limit = serializers.IntegerField(
        default=5,
        min_value=1,
        max_value=5,
    )
class ChatRequestSerializer(SearchRequestSerializer):
    conversation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )