from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import Http404
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Count

# Models
from .models import User, Profile, Community, Notification, Event, Post, PostCategory

# Forms
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordChangeForm,
    PostForm, CommunityForm
)

# DRF
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .serializers import UserSerializer
from django.db.models import Q  
from django.http import Http404

# Create your views here.
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
        privacy = request.POST.get("privacy", "public")  # ✅ default to public if not set

        profile.bio = bio
        profile.interests = interests
        profile.privacy = privacy  # ✅ save privacy selection
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
    
    return render(request, 'core/dashboard.html', {})

# Community Views
class CommunityListView(ListView):
    model = Community
    template_name = 'core/community_list.html'
    context_object_name = 'communities'

class CommunityDetailView(DetailView):
    model = Community
    template_name = 'core/community_detail.html'
    context_object_name = 'community'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['posts'] = Post.objects.filter(community=self.object).order_by('-created_at')
        context['is_member'] = self.request.user in self.object.members.all() if self.request.user.is_authenticated else False
        return context

class CommunityCreateView(LoginRequiredMixin, CreateView):
    model = Community
    form_class = CommunityForm
    template_name = 'core/community_form.html'
    
    def post(self, request, *args, **kwargs):
        # Print what's in the post data
        print(f"POST data: {request.POST}")
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Make sure to set the created_by field before saving
        form.instance.created_by = self.request.user
        # Set the slug field based on the name
        form.instance.slug = slugify(form.instance.name)
        
        # Now let the form save
        response = super().form_valid(form)
        
        # Add the current user to members
        self.object.members.add(self.request.user)
        
        return response

class JoinCommunityView(LoginRequiredMixin, DetailView):
    model = Community
    
    def get(self, request, *args, **kwargs):
        community = self.get_object()
        community.members.add(request.user)
        return redirect('core:community_detail', slug=community.slug)

class LeaveCommunityView(LoginRequiredMixin, DetailView):
    model = Community
    
    def get(self, request, *args, **kwargs):
        community = self.get_object()
        community.members.remove(request.user)
        return redirect('core:community_detail', slug=community.slug)

# Post Views
class PostDetailView(DetailView):
    model = Post
    template_name = 'core/post_detail.html'
    context_object_name = 'post'

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post_form.html'
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.community = Community.objects.get(slug=self.kwargs['slug'])
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('core:community_detail', kwargs={'slug': self.kwargs['slug']})
    
    def dispatch(self, request, *args, **kwargs):
        community = Community.objects.get(slug=self.kwargs['slug'])
        if request.user not in community.members.all():
            messages.error(request, "You must be a member to post in this community.")
            return redirect('core:community_detail', slug=self.kwargs['slug'])
        return super().dispatch(request, *args, **kwargs)

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post_form.html'
    
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author
    
    def get_success_url(self):
        return reverse_lazy('core:post_detail', kwargs={'pk': self.object.pk})

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'core/post_confirm_delete.html'
    
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author
    
    def get_success_url(self):
        return reverse_lazy('core:community_detail', kwargs={'slug': self.object.community.slug})

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
    
@login_required
def search_profiles(request):
    query = request.GET.get('q', '')
    results = []

    if query:
        results = User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).exclude(id=request.user.id)  # hide self

    return render(request, 'core/search_profiles.html', {
        'query': query,
        'results': results
    })

@login_required
def public_profile_view(request, user_id):
    try:
        profile_user = User.objects.get(id=user_id)
        profile = profile_user.profile
    except User.DoesNotExist:
        raise Http404("User not found")
    except Profile.DoesNotExist:
        raise Http404("Profile not found")

    # Privacy checks
    if profile.privacy == "private" and profile_user != request.user:
        raise Http404("This profile is private.")

    return render(request, 'core/public_profile.html', {
        'profile_user': profile_user,
        'profile': profile
    })
