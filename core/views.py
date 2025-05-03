from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Count
from django.template.loader import render_to_string
import os

# Image processing imports
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

# Models
from .models import User, Profile, Community, Notification, Event, Post, Comment, Tag, InterestTag

# Forms
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordChangeForm,
    PostForm, CommunityForm, CommentForm
)

# DRF
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .serializers import UserSerializer
from django.db.models import Q  

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
def edit_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Handle profile update
        profile.bio = request.POST.get('bio', '')
        profile.interests = request.POST.get('interests', '')
        profile.privacy = request.POST.get('privacy', 'public')
        profile.interest_tags.clear()
        
        # Check if the user wants to remove the current image
        if 'remove_image' in request.POST:
            if profile.profile_image:
                # Delete the file if it exists
                if os.path.isfile(profile.profile_image.path):
                    os.remove(profile.profile_image.path)
                profile.profile_image = None
        
        # Handle profile image upload
        if 'profile_image' in request.FILES:
            uploaded_image = request.FILES['profile_image']
            
            # Security checks for the uploaded file
            # Check file size (limit to 5MB)
            if uploaded_image.size > 5 * 1024 * 1024:
                messages.error(request, "Image file is too large (maximum 5MB allowed).")
                return render(request, 'core/edit_profile.html', {'profile': profile})
                
            # Check file type by content-type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if uploaded_image.content_type not in allowed_types:
                messages.error(request, "Only JPEG, PNG, GIF and WebP image files are allowed.")
                return render(request, 'core/edit_profile.html', {'profile': profile})
                
            # Additional check for valid extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            ext = os.path.splitext(uploaded_image.name)[1].lower()
            if ext not in valid_extensions:
                messages.error(request, "File extension not allowed.")
                return render(request, 'core/edit_profile.html', {'profile': profile})
            
            # Try to open with PIL to verify it's actually an image
            try:
                img = Image.open(uploaded_image)
                img.verify() # Verify it's an image
                uploaded_image.seek(0) # Reset file pointer after verify
                img = Image.open(uploaded_image) # Re-open for processing
                
                # Check if crop data is provided
                if 'crop_x' in request.POST and 'crop_y' in request.POST and 'crop_size' in request.POST:
                    # Get crop coordinates and size
                    x = float(request.POST.get('crop_x'))
                    y = float(request.POST.get('crop_y'))
                    size = float(request.POST.get('crop_size'))
                    
                    # Calculate crop box (left, upper, right, lower)
                    half_size = size / 2
                    left = max(0, x - half_size)
                    upper = max(0, y - half_size)
                    right = min(img.width, x + half_size)
                    lower = min(img.height, y + half_size)
                    
                    # Ensure our crop box is valid (right > left and lower > upper)
                    if right <= left or lower <= upper:
                        # Use default crop if calculated coordinates are invalid
                        dimension = min(img.width, img.height)
                        left = (img.width - dimension) // 2
                        upper = (img.height - dimension) // 2
                        right = left + dimension
                        lower = upper + dimension
                    
                    # Crop and resize the image to a square
                    cropped_img = img.crop((left, upper, right, lower))
                    output_size = (500, 500)  # Standard size for profile images
                    cropped_img = cropped_img.resize(output_size, Image.LANCZOS)
                    
                    # Save the cropped image
                    output = BytesIO()
                    if cropped_img.mode != 'RGB':
                        cropped_img = cropped_img.convert('RGB')
                    cropped_img.save(output, format='JPEG', quality=90)
                    output.seek(0)
                    
                    # Create a new file to save
                    profile_image = InMemoryUploadedFile(
                        output, 'ImageField', 
                        f"{uploaded_image.name.split('.')[0]}_cropped.jpg",
                        'image/jpeg', sys.getsizeof(output), None
                    )
                    profile.profile_image = profile_image
                else:
                    # No crop data, use original image
                    profile.profile_image = uploaded_image
                    
            except Exception as e:
                messages.error(request, f"Invalid image file: {str(e)}")
                return render(request, 'core/edit_profile.html', {'profile': profile})
        
        # Only process tags if they're in the POST data
        if 'interest_tags' in request.POST:
            # Get all tags from the form
            tag_names = request.POST.getlist('interest_tags')
            
            # Pre-process all tag names to normalize them and remove duplicates
            normalized_tag_names = set()
            for tag_name in tag_names:
                # Apply the same normalization logic as in the InterestTag model
                tag_name = tag_name.strip().strip('#').replace(' ', '').lower()
                if tag_name:  # Skip empty tags
                    normalized_tag_names.add(tag_name)
            
            # Now process the unique normalized tags
            for tag_name in normalized_tag_names:
                try:
                    # First try to get an existing tag
                    tag = InterestTag.objects.get(name=tag_name)
                except InterestTag.DoesNotExist:
                    # If it doesn't exist, create a new one
                    tag = InterestTag(name=tag_name)
                    tag.save()
                
                # Add the tag to the profile
                profile.interest_tags.add(tag)
                
        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('core:profile')

    return render(request, 'core/edit_profile.html', {'profile': profile})

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

# Community Views
class CommunityListView(ListView):
    model = Community
    template_name = 'core/community_list.html'
    context_object_name = 'communities'

class CommunityDetailView(DetailView):
    model = Community
    template_name = 'core/community_detail.html'
    context_object_name = 'community'
    
    def get_object(self, queryset=None):
        """Force a fresh database query to avoid stale leader data"""
        slug = self.kwargs.get('slug')
        # Force a completely fresh query from the database with no caching
        community = Community.objects.select_related('leader').filter(slug=slug).first()
        
        if not community:
            raise Http404("Community not found")
            
        # Double-check leader is a member
        if community.leader and community.members.filter(id=community.leader.id).count() == 0:
            community.leader = None
            community.save(update_fields=['leader'])
        
        return community
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = Post.objects.filter(community=self.object).order_by('-created_at')
        
        # Add comment count to each post
        for post in posts:
            post.comment_count = post.comments.count()
            
        context['posts'] = posts
        context['is_member'] = self.request.user in self.object.members.all() if self.request.user.is_authenticated else False
        return context

class CommunityCreateView(LoginRequiredMixin, CreateView):
    model = Community
    form_class = CommunityForm
    template_name = 'core/community_form.html'
    
    def post(self, request, *args, **kwargs):
        # Print what's in the post data
        print(f"POST data: {request.POST}")
        
        # Check if a community with the same name already exists
        community_name = request.POST.get('name')
        if community_name:
            potential_slug = slugify(community_name)
            existing_community = Community.objects.filter(slug=potential_slug).first()
            if existing_community:
                form = self.get_form()
                form.add_error('name', f'A community with this name already exists: {existing_community.name}')
                return self.form_invalid(form)
                
        return super().post(request, *args, **kwargs)
    
    def form_invalid(self, form):
        """Override form_invalid which avoids an AttributeError"""
        self.object = None
        return self.render_to_response(self.get_context_data(form=form))
    
    def form_valid(self, form):
        # Make sure to set the created_by field before saving
        form.instance.created_by = self.request.user
        # Set the slug field based on the name
        form.instance.slug = slugify(form.instance.name)
        # Set the leader as the creator
        form.instance.leader = self.request.user
        
        # Now let the form save
        response = super().form_valid(form)
        
        # Add the current user to members
        self.object.members.add(self.request.user)
        
        return response

class JoinCommunityView(LoginRequiredMixin, DetailView):
    model = Community
    
    def get(self, request, *args, **kwargs):
        community = self.get_object()
        
        # Add user to members
        community.members.add(request.user)
        
        # Check if community is leaderless and make this user the leader
        if community.leader_id is None:
            # Use ORM update instead of direct SQL
            Community.objects.filter(id=community.id, leader__isnull=True).update(leader=request.user)
            community.refresh_from_db()
            messages.success(request, "You have joined the community and become its leader!")
        else:
            messages.success(request, "You have joined the community!")
            
        return redirect('core:community_detail', slug=community.slug)

class LeaveCommunityView(LoginRequiredMixin, DetailView):
    model = Community
    
    def get(self, request, *args, **kwargs):
        community = self.get_object()
        is_leader = request.user == community.leader
        
        # Remove user from members
        community.members.remove(request.user)
        
        # If the user is the leader, handle leadership
        if is_leader:
            # Get members count after removal
            members_count = community.members.count()
            
            if members_count == 0:
                # Using ORM but with refresh_from_db to ensure consistency
                Community.objects.filter(id=community.id).update(leader=None)
                # Refresh the object to ensure it reflects the database state
                community.refresh_from_db()
                messages.warning(request, "Community is now leaderless until someone joins.")
            else:
                # Transfer leadership to another member
                earliest_member = community.members.order_by('id').first()
                Community.objects.filter(id=community.id).update(leader=earliest_member)
                community.refresh_from_db()
                messages.info(request, "Leadership has been transferred to another member.")
        
        return redirect('core:community_detail', slug=community.slug)

# Post Views
class PostDetailView(DetailView):
    model = Post
    template_name = 'core/post_detail.html'
    context_object_name = 'post'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check visibility permissions
        post = self.object
        content_restricted = False
        
        post.comment_count = Comment.objects.filter(post=post).count()
        
        # For members-only posts, check if user is authenticated and a member
        if post.visibility == 'members':
            if not self.request.user.is_authenticated or self.request.user not in post.community.members.all():
                content_restricted = True
        
        # Get only the top-level comments (no parent), sorted by newest first
        comments = Comment.objects.filter(
            post=self.object, 
            parent__isnull=True
        ).order_by('-created_at').prefetch_related('replies', 'replies__replies', 'author')
        
        context['comments'] = comments
        context['comment_form'] = CommentForm()
        context['is_member'] = self.request.user in self.object.community.members.all() if self.request.user.is_authenticated else False
        context['content_restricted'] = content_restricted
        
        return context

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post_form.html'
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.community = Community.objects.get(slug=self.kwargs['slug'])
        form.instance.visibility = form.cleaned_data.get('visibility', 'public')  # Set visibility
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
    
    def form_valid(self, form):
        form.instance.visibility = form.cleaned_data.get('visibility', 'public')  # Update visibility
        return super().form_valid(form)
    
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

# Comment Views
class CommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        
        # Check if user is a member of the community
        if request.user not in post.community.members.all():
            messages.error(request, "You must be a member to comment in this community.")
            return redirect('core:post_detail', pk=pk)
        
        content = request.POST.get('content', '').strip()
        if content:
            Comment.objects.create(
                post=post,
                author=request.user,
                content=content
            )
            messages.success(request, "Comment added successfully.")
        
        return redirect('core:post_detail', pk=pk)

class ReplyCreateView(LoginRequiredMixin, View):
    def post(self, request, post_pk, comment_pk):
        post = get_object_or_404(Post, pk=post_pk)
        parent_comment = get_object_or_404(Comment, pk=comment_pk)
        
        # Check if user is a member of the community
        if request.user not in post.community.members.all():
            messages.error(request, "You must be a member to reply in this community.")
            return redirect('core:post_detail', pk=post_pk)
        
        content = request.POST.get('content', '').strip()
        parent_reply_id = request.POST.get('parent_reply_id')
        
        if content:
            # Create the reply comment
            reply = Comment(
                post=post,
                author=request.user,
                content=content,
                parent=parent_comment
            )
            
            # If replying to a reply, set the parent_reply field
            if parent_reply_id:
                try:
                    parent_reply = Comment.objects.get(pk=parent_reply_id)
                    reply.parent_reply = parent_reply
                except Comment.DoesNotExist:
                    pass
                
            reply.save()
            messages.success(request, "Reply added successfully.")
            
        return redirect('core:post_detail', pk=post_pk)

@login_required
def add_reply(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    root_comment = get_object_or_404(Comment, pk=comment_id)
    
    # Check if the user is a member of the community
    if request.user not in post.community.members.all():
        return HttpResponseForbidden("You must be a member of this community to reply to comments.")
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_reply_id')
        
        if content:
            # Create the reply
            reply = Comment(
                post=post,
                author=request.user,
                content=content
            )
            
            # Set the correct parent
            if parent_id and parent_id != comment_id:
                reply.parent = get_object_or_404(Comment, pk=parent_id)
            else:
                reply.parent = root_comment
                
            reply.save()
            return redirect('core:post_detail', pk=post_id)
        else:
            messages.error(request, "Reply content cannot be empty")
            
    return redirect('core:post_detail', pk=post_id)

class CommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        comment = get_object_or_404(Comment, pk=self.kwargs['pk'])
        return self.request.user == comment.author
    
    def get(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        return render(request, 'core/edit_comment.html', {'comment': comment})
    
    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        content = request.POST.get('content', '').strip()
        
        if content:
            comment.content = content
            comment.save()
            messages.success(request, "Comment updated successfully.")
        else:
            messages.error(request, "Comment cannot be empty.")
            return render(request, 'core/edit_comment.html', {'comment': comment})
        
        return redirect('core:post_detail', pk=comment.post.id)

class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        comment = get_object_or_404(Comment, pk=self.kwargs['pk'])
        return self.request.user == comment.author
    
    def get(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        post_id = comment.post.id
        comment.delete()
        messages.success(request, "Comment deleted successfully.")
        return redirect('core:post_detail', pk=post_id)

def sort_comments(request, pk):
    """
    Handle AJAX requests for sorting comments by newest or oldest
    """
    post = get_object_or_404(Post, pk=pk)
    sort_option = request.GET.get('sort', 'new')
    
    # Get only the top-level comments (no parent)
    if sort_option == 'old':
        # Sort from oldest to newest (ascending by created_at)
        comments = Comment.objects.filter(
            post=post, 
            parent__isnull=True
        ).order_by('created_at').prefetch_related('replies', 'replies__replies', 'author')
    else:
        # Sort from newest to oldest (descending by created_at)
        comments = Comment.objects.filter(
            post=post, 
            parent__isnull=True
        ).order_by('-created_at').prefetch_related('replies', 'replies__replies', 'author')
    
    # Render the sorted comments to HTML
    html = ""
    for comment in comments:
        html += render_to_string(
            'core/includes/comment.html',
            {
                'comment': comment, 
                'post': post,
                'user': request.user,
                'is_member': request.user in post.community.members.all() if request.user.is_authenticated else False,
                'level': 0,
                'is_reply': False
            },
            request
        )
    
    return JsonResponse({
        'html': html,
        'count': comments.count()
    })

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
        return render(request, '404.html', {
            'error_message': 'User Not Found',
            'error_detail': 'The user you are looking for does not exist.'
        }, status=404)
    except Profile.DoesNotExist:
        return render(request, '404.html', {
            'error_message': 'Profile Not Found',
            'error_detail': 'This user does not have a profile yet.'
        }, status=404)

    # Privacy checks
    if profile.privacy == "private" and profile_user != request.user:
        return render(request, '403.html', {
            'error_message': 'Private Profile',
            'error_detail': 'This profile is private and can only be viewed by the owner.'
        }, status=403)

    return render(request, 'core/public_profile.html', {
        'profile_user': profile_user,
        'profile': profile
    })

class TagPostsView(ListView):
    """Display all posts with a specific tag"""
    model = Post
    template_name = 'core/tag_posts.html'
    context_object_name = 'posts'
    
    def get_queryset(self):
        tag_name = self.kwargs.get('tag_name')
        return Post.objects.filter(tags__name=tag_name.lower())
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag_name = self.kwargs.get('tag_name')
        context['tag_name'] = tag_name
        
        # Add community membership information for the posts
        if self.request.user.is_authenticated:
            # Get communities where the current user is a member
            user_communities = Community.objects.filter(members=self.request.user)
            
            # Add a flag to check if user is a member for each post's community
            posts = context['posts']
            for post in posts:
                post.is_member = post.community in user_communities
        
        return context
