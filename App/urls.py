from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_page, name='home'),
    path('login/', views.login_page, name='login'),
    path('editor/', views.editor_ui, name='editor'),
    path('logout/', views.logout_user, name='logout'),
    
    # API endpoints
    path('api/login/', views.login_user, name='login_user'),
    path('api/ai/', views.ai_request, name='ai_request'),
    path('api/video-to-text/', views.video_to_text, name='video_to_text'),
]