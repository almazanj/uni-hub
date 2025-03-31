from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Community

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """
    Custom form for user registration that uses email as the unique identifier
    instead of username. Extends Django's UserCreationForm.
    """
    email = forms.EmailField(max_length=254, required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    terms = forms.BooleanField(required=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2', 'terms')

    def clean_email(self):
        """
        Validate that the email is not already in use.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form that uses email as the username field.
    """
    username = forms.EmailField()
    remember_me = forms.BooleanField(required=False)

class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with better error messages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ['name', 'description']