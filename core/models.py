from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of username.
    """
    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    Custom User model where email is the unique identifier
    instead of username for authentication.
    """
    username = None
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
    
class Profile(models.Model):
    PRIVACY_CHOICES = [
        ('public', 'Public - Everyone can see your profile'),
        ('private', 'Private - Only you can see your profile'),
        ('friends', 'Friends Only - Only your friends can see your profile'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    university = models.CharField(max_length=100, blank=True)
    course = models.CharField(max_length=100, blank=True)
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='public')  # ✅ Add this line

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}'s Profile"
    
class Community(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_communities')
    members = models.ManyToManyField(User, related_name='communities')
    leader = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='led_communities', null=True)
    
    class Meta:
        verbose_name_plural = "Communities"
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        print(f"Saving community: {self.name}")
        print(f"Created by: {self.created_by}")
        
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            
            while Community.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
            
        # Check if created_by is set
        if not self.created_by_id:
            raise ValueError("Community must have a creator")
        
        # Set creator as leader if leader is not set
        if not self.leader_id and self.created_by_id:
            self.leader = self.created_by
            
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        return reverse('core:community_detail', kwargs={'slug': self.slug})
        
    def transfer_leadership(self):
        """Transfer leadership to the earliest member if the current leader leaves"""
        if not self.leader or self.leader not in self.members.all():
            # Get the earliest member who is not the current leader
            earliest_member = self.members.order_by('id').first()
            if earliest_member:
                self.leader = earliest_member
                self.save()
                return True
            else:
                # No members left, set leader to None
                self.leader = None
                self.save()
                return False

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('core:tag_posts', kwargs={'tag_name': self.name})

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='posts')
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('core:post_detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        """Extract hashtags from content when saving"""
        super().save(*args, **kwargs)
        # Process hashtags after the post is saved
        self.process_hashtags()
    
    def process_hashtags(self):
        """Extract hashtags from post content and link them to this post"""
        # Clear existing tags
        self.tags.clear()
        
        # Find all hashtags in the content using regex
        import re
        hashtags = re.findall(r'#(\w+)', self.content)
        
        # Add unique hashtags
        for tag_name in set(hashtags):
            tag, created = Tag.objects.get_or_create(name=tag_name.lower())
            self.tags.add(tag)

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=200, blank=True, null=True)
    is_virtual = models.BooleanField(default=False)
    virtual_link = models.URLField(blank=True, null=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='events')
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    participants = models.ManyToManyField(User, related_name='events', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
        
    @property
    def is_upcoming(self):
        return self.date >= timezone.now().date()

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}: {self.title}"
        
    class Meta:
        ordering = ['-created_at']

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f'Comment by {self.author.email} on {self.post.title}'