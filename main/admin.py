from django.contrib import admin
from .models import ai_generated_playlist, listening_analytics, playlist_user, playlist_song
# Register your models here.
admin.site.register(playlist_user)
admin.site.register(playlist_song)
admin.site.register(ai_generated_playlist)
admin.site.register(listening_analytics)