from rest_framework import serializers

from .models import Playlist, Track


class TrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = ["id", "title", "url", "position"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "title": {"max_length": 200},
            "url": {"max_length": 2048},
            "position": {"min_value": 0},
        }


class PlaylistSerializer(serializers.ModelSerializer):
    tracks = TrackSerializer(many=True, read_only=True)
    track_count = serializers.IntegerField(source="tracks.count", read_only=True)
    follower_count = serializers.IntegerField(source="follows.count", read_only=True)

    class Meta:
        model = Playlist
        fields = [
            "id",
            "name",
            "is_public",
            "owner_id",
            "created_at",
            "tracks",
            "track_count",
            "follower_count",
        ]
        read_only_fields = ["id", "owner_id", "created_at"]


class PlaylistCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        fields = ["name", "is_public"]


class TrackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Track
        fields = ["title", "url", "position"]
        extra_kwargs = {
            "title": {"max_length": 200},
            "url": {"max_length": 2048},
            "position": {"min_value": 0, "required": False},
        }
