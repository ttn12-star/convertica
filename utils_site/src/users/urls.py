from django.urls import path

from . import social_views, views

app_name = "users"

urlpatterns = [
    path("login/", views.user_login, name="login"),
    path("register/", views.user_register, name="register"),
    path("logout/", views.user_logout, name="logout"),
    path("profile/", views.user_profile, name="profile"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile_edit"),
    path(
        "google-direct/", social_views.google_direct_oauth, name="google_direct_oauth"
    ),
]
