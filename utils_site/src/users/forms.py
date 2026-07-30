from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class LoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": _("Enter your email"),
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": _("Enter your password"),
            }
        ),
    )


def _is_claimed_account(user) -> bool:
    """True if the account is genuinely in use and must never be recycled."""
    from allauth.account.models import EmailAddress

    if user.is_staff or user.is_superuser or user.is_premium:
        return True
    # SOCIALACCOUNT_EMAIL_VERIFICATION="optional": a Google user can log in and
    # use the site without ever owning a verified EmailAddress row.
    if user.socialaccount_set.exists():
        return True
    return EmailAddress.objects.filter(user=user, verified=True).exists()


def stale_unverified_user(email: str):
    """Return the abandoned unverified account holding `email`, if any.

    Nobody ever proved they own that address — typically a spam bot squatting a
    harvested one. Keeping the row would block the real owner from registering
    until the 30-day cleanup task removes it, so the signup view drops it first.
    """
    email = (email or "").strip()
    if not email:
        return None
    existing = User.objects.filter(email=email).first()
    if existing is None or _is_claimed_account(existing):
        return None
    return existing


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": _("Enter your email"),
            }
        ),
    )
    username = forms.CharField(
        label=_("Username"),
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": _("Choose a username"),
            }
        ),
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": _("Enter your password"),
            }
        ),
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": _("Confirm your password"),
            }
        ),
    )
    agree_terms = forms.BooleanField(
        label=_("I agree to the Terms of Service and Privacy Policy"),
        required=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            }
        ),
    )

    class Meta:
        model = User
        fields = ("email", "username", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email
