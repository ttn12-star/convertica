import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def __init__(self, request=None):  # pylint: disable=useless-super-delegation
        # request parameter is required by allauth interface
        super().__init__(request)

    def pre_social_login(self, request, sociallogin):
        # Custom logic for pre-social login if needed
        pass

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        return user

    def get_login_redirect_url(self, request):  # pylint: disable=unused-argument
        """Redirect to profile after successful OAuth"""
        # request parameter is required by allauth interface
        return "/users/profile/"

    def get_connect_redirect_url(
        self, request, socialaccount=None
    ):  # pylint: disable=unused-argument
        """Redirect to profile after connecting account"""
        # request and socialaccount parameters are required by allauth interface
        return "/users/profile/"
