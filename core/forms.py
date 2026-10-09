from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from uuid import uuid4
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    display_name = forms.CharField(
        required=True,
        max_length=50,
        label=_("Nickname (shown during lessons)"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Mika, Tom...")}),
    )
    referral_source = forms.CharField(
        required=False,
        max_length=300,
        label=_("How did you hear about us?"),
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Instagram, friend, Google...")}),
        help_text=_("Optional."),
    )

    class Meta:
        model = User
        fields = ("email", "display_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("This email address is already registered."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = "member_" + uuid4().hex
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("display_name", "")
        if commit:
            user.save()
        return user


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Email address (or username)"),
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
