from rest_framework import serializers


class FeedbackSerializer(serializers.Serializer):
    feedback_token = serializers.CharField(max_length=500)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )

    def validate(self, data):
        if data["rating"] <= 3 and not (data.get("comment") or "").strip():
            raise serializers.ValidationError(
                {"comment": "A comment is required for ratings of 3 stars or below."}
            )
        return data
