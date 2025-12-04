
from django.conf import settings

def hreflang_links(request):

    current_path = request.path
    languages = getattr(settings, 'LANGUAGES', [('en', 'English')])
    
    hreflangs = []
    for code, _ in languages:
        url = f"{request.scheme}://{request.get_host()}{current_path}?lang={code}"
        hreflangs.append({
            'code': code,
            'url': url
        })
    
    hreflangs.append({
        'code': 'x-default',
        'url': f"{request.scheme}://{request.get_host()}{current_path}"
    })

    return {'hreflangs': hreflangs}
