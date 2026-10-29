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


class ConversationNoteForm(forms.Form):
    learner_level = forms.CharField(required=False)
    talked_about = forms.CharField(required=False, max_length=500)
    next_conversation = forms.CharField(required=False, max_length=500)
    conversation_not_held = forms.BooleanField(required=False)

    def clean_learner_level(self):
        from core.models import ConversationNote
        level = self.cleaned_data['learner_level']
        return level if level in dict(ConversationNote.LEVEL_CHOICES) else ''

    def clean(self):
        data = super().clean()
        if not data.get('conversation_not_held'):
            for field in ('talked_about', 'next_conversation'):
                if field not in self.errors and not data.get(field):
                    self.add_error(field, _("Complete this field, or select 'Conversation did not take place'."))
        return data
