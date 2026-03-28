from django.db import models


# Create your models here.
class playlist_user(models.Model):
    username = models.CharField(max_length=200)

    def __str__(self):
        return f'Username = {self.username}, Liked Songs = {list(self.playlist_song_set.all())}'

class playlist_song(models.Model):
    user = models.ForeignKey(playlist_user, on_delete=models.CASCADE)
    song_title = models.CharField(max_length=200)
    song_youtube_id =  models.CharField(max_length=20)
    song_albumsrc = models.CharField(max_length=255)
    song_dur = models.CharField(max_length=7)
    song_channel = models.CharField(max_length=100)
    song_date_added = models.CharField(max_length=12)

    def __str__(self):
      return f'Title = {self.song_title}, Date = {self.song_date_added}'


class ai_generated_playlist(models.Model):
    user = models.ForeignKey(playlist_user, on_delete=models.CASCADE)
    prompt = models.TextField()
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True, default="")
    queries = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class listening_analytics(models.Model):
    EVENT_PLAY = "play"
    EVENT_COMPLETE = "complete"
    EVENT_SKIP = "skip"
    EVENT_CHOICES = (
        (EVENT_PLAY, "Play"),
        (EVENT_COMPLETE, "Complete"),
        (EVENT_SKIP, "Skip"),
    )

    user = models.ForeignKey(playlist_user, on_delete=models.CASCADE)
    song_youtube_id = models.CharField(max_length=20, blank=True, default="")
    song_title = models.CharField(max_length=220, blank=True, default="")
    genre = models.CharField(max_length=80, blank=True, default="unknown")
    mood = models.CharField(max_length=80, blank=True, default="unknown")
    listen_seconds = models.PositiveIntegerField(default=0)
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES, default=EVENT_PLAY)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.song_title} ({self.event_type})"


