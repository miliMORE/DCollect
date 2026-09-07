from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from catalog.models import County

from .models import User


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"autofocus": True, "autocomplete": "username"})
        self.fields["password"].widget.attrs.update({"autocomplete": "current-password"})
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class PlatformUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}),
        required=False,
        help_text="Leave blank to keep the current password when editing.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}),
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "county",
            "phone",
            "job_title",
            "is_active",
            "must_change_password",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "input"}),
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "role": forms.Select(attrs={"class": "input"}),
            "county": forms.Select(attrs={"class": "input"}),
            "phone": forms.TextInput(attrs={"class": "input"}),
            "job_title": forms.TextInput(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)
        self.fields["county"].queryset = County.objects.filter(is_active=True)
        self.fields["county"].required = False
        self.fields["county"].help_text = "Required for county respondents. Leave blank for other roles."
        self.fields["role"].help_text = (
            "Administrator owns the site name and help text. Collection administrator manages "
            "jobs, counties, files and users. Consultant reviews files. Analyst downloads reports. "
            "County respondent fills one county file."
        )
        self.fields["must_change_password"].help_text = "Ask this person to set their own password at next sign-in."
        self.fields["is_active"].help_text = "Inactive users cannot sign in."
        if self.request_user and not self.request_user.can_edit_site:
            self.fields["role"].choices = [
                (value, label)
                for value, label in User.Role.choices
                if value != User.Role.ADMIN
            ]
        if not self.instance.pk:
            self.fields["password1"].required = True
            self.fields["password2"].required = True
            self.fields["must_change_password"].initial = True

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        county = cleaned.get("county")
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        actor = self.request_user
        if actor and not actor.can_edit_site:
            if self.instance.pk and self.instance.role == User.Role.ADMIN:
                self.add_error(None, "You cannot edit a platform administrator account.")
            if role == User.Role.ADMIN:
                self.add_error("role", "Only a platform administrator can create or change administrator accounts.")
        if role == User.Role.COUNTY and not county:
            self.add_error("county", "County respondents must be linked to one county.")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "The two passwords do not match.")
            elif p1 and len(p1) < 10:
                self.add_error("password1", "Password must be at least 10 characters.")
        elif not self.instance.pk:
            self.add_error("password1", "Set an initial password.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if user.role == User.Role.ADMIN:
            user.is_staff = True
        else:
            user.is_staff = bool(user.is_superuser)
        if user.role != User.Role.COUNTY:
            user.county = None
        if commit:
            user.save()
        return user
