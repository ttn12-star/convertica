from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import UpdateView

from .forms import CustomUserCreationForm, LoginForm


def user_login(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect("users:profile")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(
                request,
                username=cd["email"],  # Using email as username
                password=cd["password"],
            )
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect("users:profile")
                else:
                    return render(
                        request,
                        "users/login.html",
                        {"form": form, "error": _("Account is disabled")},
                    )
            else:
                return render(
                    request,
                    "users/login.html",
                    {"form": form, "error": _("Invalid email or password")},
                )
    else:
        form = LoginForm()

    return render(request, "users/login.html", {"form": form})


def user_register(request):
    """Handle user registration."""
    if request.user.is_authenticated:
        return redirect("users:profile")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in after registration
            login(request, user)
            return redirect("users:profile")
    else:
        form = CustomUserCreationForm()

    return render(request, "users/register.html", {"form": form})


def user_logout(request):
    """Handle user logout."""
    logout(request)
    return redirect("users:login")


@login_required
def user_profile(request):
    """Display user profile."""
    return render(request, "users/profile.html", {"user": request.user})


class ProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update user profile."""

    fields = ["username", "first_name", "last_name"]
    template_name = "users/profile_edit.html"
    success_url = reverse_lazy("users:profile")
    success_message = _("Profile updated successfully!")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Profile")
        return context
