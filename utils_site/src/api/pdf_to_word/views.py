from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from pdf2docx import Converter
from django.core.files.storage import default_storage
from django.http import FileResponse
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import PDFToWordSerializer
import os


class PDFToWordAPIView(APIView):
    """
    API View to handle PDF to Word conversion.

    Accepts a PDF file via POST request and returns a .docx file.
    """

    @swagger_auto_schema(
        operation_description="Convert a PDF file to Word (.docx)",
        request_body=PDFToWordSerializer,
        responses={
            200: openapi.Response(
                description="Converted Word file",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            ),
            400: "Bad request, invalid PDF file",
            500: "Internal server error"
        },
        consumes=["multipart/form-data"]
    )
    def post(self, request):
        """
        Handle POST request with a PDF file.

        Args:
            request: DRF request object containing 'pdf_file'.

        Returns:
            FileResponse: A Word file converted from the uploaded PDF.
        """
        serializer = PDFToWordSerializer(data=request.data)
        if serializer.is_valid():
            pdf_file = serializer.validated_data.get("pdf_file")
            if not pdf_file:
                return Response(
                    {"error": "pdf_file is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                pdf_path = default_storage.save(f"temp/{pdf_file.name}", pdf_file)
                word_path = pdf_path.replace(".pdf", ".docx")

                cv = Converter(default_storage.path(pdf_path))
                cv.convert(default_storage.path(word_path))
                cv.close()

                response = FileResponse(
                    open(default_storage.path(word_path), "rb"),
                    as_attachment=True,
                    filename=os.path.basename(word_path)
                )

                default_storage.delete(pdf_path)
                default_storage.delete(word_path)

                return response
            except Exception as e:
                return Response(
                    {"error": f"Conversion failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
