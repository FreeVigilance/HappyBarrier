from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group

from core.validators import PhoneNumberValidator
from users.models import User


class AdminCreationForm(forms.ModelForm):
    """Custom form for creating an admin via Django Admin"""

    phone = forms.CharField(
        label="Phone",
        validators=[PhoneNumberValidator()],
        help_text="Enter a valid phone number in the format +7XXXXXXXXXX.",
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Set a password for the new admin.",
    )

    class Meta:
        model = User
        fields = ("phone", "full_name", "password")

    def save(self, commit=True):
        """Creates an admin user"""

        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_staff = True  # Ensure it's an admin
        user.role = User.Role.ADMIN
        if commit:
            user.save()
        return user


class UserAdmin(BaseUserAdmin):
    """Custom UserAdmin for managing users in Django Admin"""

    def add_view(self, request, form_url="", extra_context=None):
        """Change the page title from 'Add user' to 'Add admin'"""

        extra_context = extra_context or {}
        extra_context["title"] = "Add admin"
        return super().add_view(request, form_url, extra_context)

    def has_view_permission(self, request, obj=None):
        """Allows active admins and superusers to view users"""

        return request.user.is_staff and request.user.is_active

    def has_module_permission(self, request):
        """Allows active admins and superusers to see Users module in the admin panel"""

        return request.user.is_staff and request.user.is_active

    def has_add_permission(self, request):
        """Only superusers can create new users"""

        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Prevent user deletion"""

        return False

    def save_model(self, request, obj, form, change):
        """Prevents superusers from deactivating themselves"""

        if change and obj == request.user and not obj.is_active:
            self.message_user(request, "You cannot deactivate your own account.", level="error")
            return

        super().save_model(request, obj, form, change)

    list_display = ("phone", "full_name", "role", "is_active", "is_staff", "is_superuser")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("phone", "full_name")
    ordering = ("phone",)
    readonly_fields = (
        "role",
        "phone_privacy",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
    )

    fieldsets = (("User Info", {"fields": (*readonly_fields, "is_active")}),)

    add_form = AdminCreationForm  # Use custom form
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "full_name", "password"),
            },
        ),
    )


class CustomAuthenticationForm(AuthenticationForm):
    def clean_username(self):
        phone = self.cleaned_data.get("username")
        validator = PhoneNumberValidator()
        validator(phone)
        return phone


# Register the model in admin
admin.site.register(User, UserAdmin)
# Delete the model for Groups managing
admin.site.unregister(Group)

# Add custom errors into login form
admin.site.login_form = CustomAuthenticationForm
