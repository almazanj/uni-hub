from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter

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
    path('communities/', views.list_communities, name='list_communities'),
    path('communities/create/', views.create_community, name='create_community'),
    path('community/<int:community_id>/', views.community_details, name='community_details'),
    path('community/<int:community_id>/edit/', views.edit_community, name='edit_community'),
    path('community/<int:community_id>/join/', views.join_community, name='join_community'),
    path('community/<int:community_id>/leave/', views.leave_community, name='leave_community'),
    path('community/<int:community_id>/delete/', views.delete_community, name='delete_community'),
    path('manage/communities/<int:community_id>/delete/', views.delete_community, name='delete_community'),
    path('manage/communities/', views.admin_community_list, name='admin_community_list'),
    path('manage/communities/<int:community_id>/edit/', views.edit_community, name='edit_community'),


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
]
