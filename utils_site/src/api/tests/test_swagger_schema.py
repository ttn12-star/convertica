"""Regression test for OpenAPI/Swagger schema generation (/api/docs/).

drf-yasg raises SwaggerGenerationError("cannot add form parameters when the
request has a request body ...") when a file-upload view exposes IN_FORM
parameters but drf-yasg also infers a JSON request body — which happens when
JSONParser is among the view's parsers and the operation isn't marked as
multipart. This test builds the full public schema (exactly what /api/docs/
does) and fails if any endpoint reintroduces that conflict.
"""

from __future__ import annotations

from django.test import SimpleTestCase
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator


class SwaggerSchemaGenerationTests(SimpleTestCase):
    def test_public_schema_generates_without_error(self):
        generator = OpenAPISchemaGenerator(
            info=openapi.Info(title="Convertica API", default_version="v1")
        )
        # Must not raise SwaggerGenerationError. public=True mirrors the live
        # SchemaView used by /api/docs/.
        schema = generator.get_schema(request=None, public=True)
        self.assertIsNotNone(schema)
