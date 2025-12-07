from rest_framework import serializers


class WordToPDFSerializer(serializers.Serializer):
    """
    Serializer for uploading a DOCX file to convert it to PDF.
    """

    word_file = serializers.FileField(
        help_text="DOCX file to be converted into PDF format."
    )
