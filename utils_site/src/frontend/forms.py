"""Forms for frontend application."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ContactForm(forms.Form):
    """Contact form for sending messages."""

    name = forms.CharField(
        max_length=100,
        required=True,
        label=_("Your Name"),
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white text-gray-900",
                "placeholder": _("Enter your name"),
            }
        ),
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        label=_("Your Email"),
        widget=forms.EmailInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white text-gray-900",
                "placeholder": _("your.email@example.com"),
            }
        ),
    )
    subject = forms.CharField(
        max_length=200,
        required=True,
        label=_("Subject"),
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white text-gray-900",
                "placeholder": _("Enter subject"),
            }
        ),
    )
    message = forms.CharField(
        required=True,
        label=_("Message"),
        widget=forms.Textarea(
            attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white text-gray-900 resize-y",
                "rows": 6,
                "placeholder": _("Enter your message"),
            }
        ),
    )
    privacy = forms.BooleanField(
        required=True,
        label=_("I agree to the Privacy Policy"),
        widget=forms.CheckboxInput(
            attrs={
                "class": "mt-1 mr-3 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500",
            }
        ),
    )

    def clean_message(self):
        """Validate message length."""
        message = self.cleaned_data.get("message", "")
        if len(message.strip()) < 10:
            raise ValidationError(_("Message must be at least 10 characters long."))
        if len(message) > 5000:
            raise ValidationError(_("Message is too long. Maximum 5000 characters."))
        return message
