from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Post, Community, Comment, Event

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
        # customize field attributes or help text here if needed
# Forms here will only be used for data validation and not mix with presentation logic.

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'visibility']

class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ['name', 'description']
        exclude = ['created_by', 'slug']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']

class EventForm(forms.ModelForm):
    """
    Form for creating and updating events.
    """
    required_materials = forms.CharField(
        widget=forms.Textarea,
        required=False,
        help_text="Optional. List any materials participants should bring."
    )
    
    class Meta:
        model = Event
        fields = ['title', 'description', 'date', 'start_time', 'end_time', 
                    'location', 'is_virtual', 'virtual_link', 'max_participants',
                    'required_materials']
        
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        is_virtual = cleaned_data.get('is_virtual')
        virtual_link = cleaned_data.get('virtual_link')
        location = cleaned_data.get('location')
        
        # Validate that end time is after start time
        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', 'End time must be after start time')
        
        # Validate that virtual events have a link
        if is_virtual and not virtual_link:
            self.add_error('virtual_link', 'Virtual events must have a meeting link')
        
        # Validate that non-virtual events have a location
        if not is_virtual and not location:
            self.add_error('location', 'In-person events must have a location')
            
        return cleaned_data