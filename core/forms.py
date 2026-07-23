from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    display_name = forms.CharField(
        required=False,
        max_length=50,
        label="Nickname (shown during lessons)",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Mika, Tom…"}),
        help_text="Optional. If blank, your username will be used.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "display_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("display_name", "")
        if commit:
            user.save()
        return user
