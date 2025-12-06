from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from pathlib import Path
from utils_site.swagger import schema_view

# Get admin URL path from settings (defaults to 'admin' for backward compatibility)
ADMIN_URL_PATH = getattr(settings, 'ADMIN_URL_PATH', 'admin')

@require_http_methods(["GET"])
def robots_txt(request):
    """Serve robots.txt file with dynamic sitemap URL."""
    robots_path = Path(__file__).resolve().parent.parent / 'static' / 'robots.txt'
    base_url = f"{request.scheme}://{request.get_host()}"
    
    try:
        with open(robots_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Replace hardcoded sitemap URL with dynamic one
        content = content.replace('https://convertica.com/sitemap.xml', f'{base_url}/sitemap.xml')
        return HttpResponse(content, content_type='text/plain')
    except FileNotFoundError:
        robots_content = f'User-agent: *\nAllow: /\n\n# Disallow admin and API endpoints\nDisallow: /admin/\nDisallow: /api/\n\n# Sitemap\nSitemap: {base_url}/sitemap.xml\n'
        return HttpResponse(robots_content, content_type='text/plain')

@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for Docker and load balancers."""
    from django.db import connection
    from django.core.cache import cache
    
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check cache connection
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        
        return HttpResponse('OK', content_type='text/plain', status=200)
    except Exception as e:
        return HttpResponse(f'ERROR: {str(e)}', content_type='text/plain', status=503)

urlpatterns = [
    path('api/', include('src.api.urls')),
    path('i18n/setlang/', set_language, name='set_language'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('health/', health_check, name='health_check'),
]

urlpatterns += i18n_patterns(
    # Admin panel with custom URL path (from settings)
    path(f'{ADMIN_URL_PATH}/', admin.site.urls),
    path('blog/', include('src.blog.urls')),
    path('', include('src.frontend.urls')),
)

if settings.DEBUG:
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    ]
