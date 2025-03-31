from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordChangeForm, CommunityForm
from .models import Profile, Community, Notification, Event, User
from django.utils import timezone
from django.db.models import Count

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from .models import Message

# DRF
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from .serializers import UserSerializer

# Create your views here.

def is_admin(user):
    return user.is_superuser

def learn_more(request):
    return render(request, "core/learn_more.html")

def home(request):
    """
    View function for the home page of the site.
    """
    return render(request, 'core/home.html')

# Web views (HTML templates)
def terms_of_service(request):
    return render(request, 'core/terms_of_service.html')

def privacy_policy(request):
    return render(request, 'core/privacy_policy.html')
def register_view(request):
    """
    Web view function for user registration.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome to Uni Hub.")
            return redirect('core:home')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'core/registration.html', {'form': form})

def login_view(request):
    """
    Web view function for user login.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
        
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')
            
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                if not remember_me:
                    # Session expires when browser closes
                    request.session.set_expiry(0)
                messages.success(request, f"Welcome back, {user.first_name if user.first_name else user.email}!")
                return redirect('core:home')
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'core/login.html', {'form': form})

@login_required
def logout_view(request):
    """
    Web view function for user logout.
    """
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('core:home')

@login_required
def profile_view(request):
    return render(request, 'core/profile.html', {'user': request.user})

@login_required
def edit_profile_view(request):
    # Ensure user has a profile (create if missing)
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        bio = request.POST.get("bio", "")
        interests = request.POST.get("interests", "")

        profile.bio = bio
        profile.interests = interests
        profile.save()

        return redirect("core:profile")  # Redirect back to profile page

    return render(request, "core/edit_profile.html", {"profile": profile})

@login_required
def change_password_view(request):
    """
    Web view function for changing user password.
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Keep the user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")
            return redirect('core:profile')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'core/change_password.html', {'form': form})

@login_required
def dashboard(request):
    
    user_communities = Community.objects.filter(members=request.user)
    
    
    recommended_communities = Community.objects.exclude(
        members=request.user
    ).annotate(
        member_count=Count('members')
    ).order_by('-member_count')[:5]
    
    # Get notifications for the user
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    # Get upcoming events
    upcoming_events = Event.objects.filter(
        date__gte=timezone.now().date()
    ).order_by('date', 'start_time')[:5]
    
    context = {
        'user_communities': user_communities,
        'recommended_communities': recommended_communities,
        'notifications': notifications,
        'upcoming_events': upcoming_events,
    }
    
    return render(request, 'core/dashboard.html', context)

@login_required
def create_community(request):
    if request.method == 'POST':
        form = CommunityForm(request.POST)
        if form.is_valid():
            community = form.save(commit=False)
            community.created_by = request.user
            community.save()
            community.members.add(request.user)
            return redirect('core:list_communities')
    else:
        form = CommunityForm()
    return render(request, 'core/create_community.html', {'form': form})

@login_required
def community_details(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    is_member = request.user in community.members.all()

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(community=community, user=request.user, content=content)
            return redirect('core:community_details', community_id=community.id)

    messages = community.messages.select_related('user').order_by('-created_at')

    return render(request, 'core/community_details.html', {
        'community': community,
        'is_member': is_member,
        'messages': messages,
    })

@login_required
def join_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if request.user not in community.members.all():
        community.members.add(request.user)
        messages.success(request, "You have joined the community.")
    else:
        messages.error(request, "You are already a member of this community.")
    return redirect('core:community_details', community_id=community_id)

@login_required
def leave_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if request.user in community.members.all():
        community.members.remove(request.user)
        messages.success(request, "You have left the community.")
    else:
        messages.error(request, "You are not a member of this community.")
    return redirect('core:community_details', community_id=community_id)

@login_required
def list_communities(request):
    communities = Community.objects.all()
    return render(request, 'core/list_communities.html', {'communities': communities})


@login_required
def edit_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if not request.user.is_superuser:
        return HttpResponseForbidden("You are not allowed to edit this community.")

    if request.method == 'POST':
        form = CommunityForm(request.POST, instance=community)
        if form.is_valid():
            form.save()
            return redirect('core:admin_community_list') 
    else:
        form = CommunityForm(instance=community)

    return render(request, 'core/edit_community.html', {'form': form, 'community': community})



#Admin deletion function for communities

@staff_member_required
def delete_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    community.delete()
    messages.success(request, "Community deleted successfully.")
    return redirect('core:admin_community_list')


@staff_member_required
def admin_community_list(request):
    communities = Community.objects.all()
    return render(request, 'core/admin_community_list.html', {'communities': communities})

@login_required
@user_passes_test(is_admin)
def manage_communities(request):
    communities = Community.objects.all()
    return render(request, 'core/manage_communities.html', {'communities': communities})

# API Views
class UserListAPIView(APIView):
    """
    API view to retrieve a list of all registered users.
    Only accessible to admin users for security reasons.
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request, format=None):
        """
        Get a list of all users with their details.
        """
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        
        # Get count of users
        user_count = users.count()
        
        # Return user data along with additional information
        response_data = {
            'count': user_count,
            'users': serializer.data,
            'admin_count': User.objects.filter(is_staff=True).count(),
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
