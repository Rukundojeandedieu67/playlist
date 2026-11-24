import uuid

from django.db import models


class Playlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    is_public = models.BooleanField(default=False)
    owner_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "name"]


class Track(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(
        Playlist, related_name="tracks", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200)
    url = models.URLField(max_length=2048)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["playlist", "position"],
                name="unique_track_position_per_playlist",
            )
        ]


class PlaylistFollow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(
        Playlist, related_name="follows", on_delete=models.CASCADE
    )
    user_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["playlist", "user_id"], name="unique_playlist_follower"
            )
        ]
