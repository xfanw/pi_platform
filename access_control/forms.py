from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class UserCreateForm(forms.ModelForm):
    display_name = forms.CharField(max_length=150, required=False)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = ["username", "email"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["display_name"].strip()
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    display_name = forms.CharField(max_length=150, required=False)
    status = forms.ChoiceField(choices=[("active", "Active"), ("inactive", "Inactive")])

    class Meta:
        model = User
        fields = ["email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["display_name"].initial = self.instance.get_full_name()
            self.fields["status"].initial = "active" if self.instance.is_active else "inactive"

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["display_name"].strip()
        user.is_active = self.cleaned_data["status"] == "active"
        user.last_name = ""
        if commit:
            user.save(update_fields=["first_name", "last_name", "email", "is_active"])
        return user


class PasswordResetForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        validators=[validate_password],
    )
