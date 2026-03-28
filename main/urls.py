from django.urls import path
from . import views

urlpatterns = [
    path("", views.default, name='default'),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_auth, name="login_auth"),  
    path("logout/", views.logout_auth, name="logout_auth"),
    path("playlist/", views.playlist, name='your_playlists'),
    path("search/", views.search, name='search_page'),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),
    path("analytics/track/", views.analytics_track, name="analytics_track"),
    path("like/toggle/", views.toggle_like, name="toggle_like"),
    path("ai/chat/", views.ai_chat, name="ai_chat"),
    path("ai/playlist/", views.ai_playlist, name="ai_playlist"),
    path("ai/command/", views.ai_command, name="ai_command"),
    path("ai/search/", views.ai_search, name="ai_search"),
    path("get_audio_url/<str:video_id>/", views.get_audio_url, name='get_audio_url'),
    path("get_audio_stream/<str:video_id>/", views.get_audio_stream, name='get_audio_stream'),
]