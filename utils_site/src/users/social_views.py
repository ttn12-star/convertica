import urllib.parse

from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.shortcuts import redirect


class GoogleDirectOAuthView:
    def __init__(self):
        # Get Google OAuth app from database
        try:
            site = Site.objects.get(id=settings.SITE_ID)
            google_app = SocialApp.objects.get(provider="google", sites=site)
            self.client_id = google_app.client_id
        except (SocialApp.DoesNotExist, Site.DoesNotExist):
            # Fallback to hardcoded value
            self.client_id = "542121284706-gnpklp992hic5tni5k9ffqum4q8gsk9c.apps.googleusercontent.com"

        # Use dynamic redirect URI based on current site
        self.redirect_uri = f"{settings.SITE_URL}/accounts/google/login/callback/"
        self.scope = "openid email profile"

    def get_auth_url(self):
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "response_type": "code",
            "access_type": "online",
        }

        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        return f"{base_url}?{urllib.parse.urlencode(params)}"


def google_direct_oauth(_request):
    """Direct redirect to Google OAuth without intermediate page"""
    oauth = GoogleDirectOAuthView()
    auth_url = oauth.get_auth_url()
    return redirect(auth_url)
