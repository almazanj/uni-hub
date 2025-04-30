from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import (
    CommunityListView, CommunityDetailView, CommunityCreateView,
    JoinCommunityView, LeaveCommunityView, 
    PostDetailView, PostCreateView, PostUpdateView, PostDeleteView,
    CommentCreateView, ReplyCreateView, CommentUpdateView, CommentDeleteView
)

# Create a router for viewsets
router = DefaultRouter()

app_name = 'core'

# Web routes (HTML responses)
web_patterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'), 
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("learn-more/", views.learn_more, name="learn_more"),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('search/', views.search_profiles, name='search_profiles'),
    path('user/<int:user_id>/', views.public_profile_view, name='view_profile'),

]

urlpatterns = [
    *web_patterns,
    
    # API routes (JSON responses) for DRF
    path('api/', include([
        # Router-generated resource endpoints
        *router.urls,
        # Manual resource endpoints
        path('users/', views.UserListAPIView.as_view(), name='user-list'),
    ])),
    
    # Community URLs
    path('communities/', CommunityListView.as_view(), name='community_list'),
    path('communities/new/', CommunityCreateView.as_view(), name='community_create'),
    path('communities/<slug:slug>/', CommunityDetailView.as_view(), name='community_detail'),
    path('communities/<slug:slug>/join/', JoinCommunityView.as_view(), name='join_community'),
    path('communities/<slug:slug>/leave/', LeaveCommunityView.as_view(), name='leave_community'),
    
    # Post URLs
    path('communities/<slug:slug>/post/new/', PostCreateView.as_view(), name='post_create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
    path('posts/<int:pk>/edit/', PostUpdateView.as_view(), name='post_update'),
    path('posts/<int:pk>/delete/', PostDeleteView.as_view(), name='post_delete'),
    
    # Comment URLs
    path('posts/<int:pk>/comment/', CommentCreateView.as_view(), name='add_comment'),
    path('posts/<int:post_pk>/comment/<int:comment_pk>/reply/', ReplyCreateView.as_view(), name='add_reply'),
    path('comments/<int:pk>/edit/', CommentUpdateView.as_view(), name='edit_comment'),
    path('comments/<int:pk>/delete/', CommentDeleteView.as_view(), name='delete_comment'),
]