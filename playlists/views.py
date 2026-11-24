from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Playlist, PlaylistFollow, Track
from .pagination import PlaylistPagination
from .permissions import IsPlaylistUser
from .serializers import (
    PlaylistCreateSerializer,
    PlaylistSerializer,
    TrackCreateSerializer,
    TrackSerializer,
)


class PlaylistListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsPlaylistUser]
    pagination_class = PlaylistPagination

    def get_queryset(self):
        return (
            Playlist.objects.filter(
                Q(is_public=True) | Q(owner_id=self.request.user.id)
            )
            .annotate(track_count=Count("tracks", distinct=True))
            .annotate(follower_count=Count("follows", distinct=True))
            .order_by("-created_at", "name", "id")
        )

    def get_serializer_class(self):
        return PlaylistCreateSerializer if self.request.method == "POST" else PlaylistSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        playlist = serializer.save(owner_id=request.user.id)
        return Response(
            PlaylistSerializer(playlist).data, status=status.HTTP_201_CREATED
        )


class PlaylistDetailView(APIView):
    permission_classes = [IsPlaylistUser]

    def get_playlist(self, request, playlist_id, owner_only=False):
        queryset = Playlist.objects.all()
        if owner_only:
            queryset = queryset.filter(owner_id=request.user.id)
        else:
            queryset = queryset.filter(
                Q(is_public=True) | Q(owner_id=request.user.id)
            )
        return get_object_or_404(queryset, id=playlist_id)

    def get(self, request, playlist_id):
        playlist = self.get_playlist(request, playlist_id)
        return Response(PlaylistSerializer(playlist).data)

    def patch(self, request, playlist_id):
        playlist = self.get_playlist(request, playlist_id, owner_only=True)
        serializer = PlaylistCreateSerializer(
            playlist, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        playlist = serializer.save()
        return Response(PlaylistSerializer(playlist).data)

    def delete(self, request, playlist_id):
        playlist = self.get_playlist(request, playlist_id, owner_only=True)
        playlist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlaylistTrackListCreateView(APIView):
    permission_classes = [IsPlaylistUser]

    def get_playlist(self, request, playlist_id, owner_only=False):
        queryset = Playlist.objects.all()
        if owner_only:
            queryset = queryset.filter(owner_id=request.user.id)
        else:
            queryset = queryset.filter(
                Q(is_public=True) | Q(owner_id=request.user.id)
            )
        return get_object_or_404(queryset, id=playlist_id)

    def get(self, request, playlist_id):
        playlist = self.get_playlist(request, playlist_id)
        return Response(TrackSerializer(playlist.tracks.all(), many=True).data)

    def post(self, request, playlist_id):
        playlist = self.get_playlist(request, playlist_id, owner_only=True)
        serializer = TrackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        last_position = playlist.tracks.order_by("-position").values_list(
            "position", flat=True
        ).first()
        position = serializer.validated_data.get(
            "position", last_position + 1 if last_position is not None else 0
        )
        try:
            with transaction.atomic():
                track = serializer.save(playlist=playlist, position=position)
        except IntegrityError as error:
            raise ValidationError(
                {"position": "A track already uses this position."}
            ) from error
        return Response(
            TrackSerializer(track).data, status=status.HTTP_201_CREATED
        )


class TrackDetailView(APIView):
    permission_classes = [IsPlaylistUser]

    def get_track(self, request, track_id):
        return get_object_or_404(
            Track.objects.filter(playlist__owner_id=request.user.id), id=track_id
        )

    def patch(self, request, track_id):
        track = self.get_track(request, track_id)
        serializer = TrackSerializer(track, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, track_id):
        self.get_track(request, track_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReorderTracksView(APIView):
    permission_classes = [IsPlaylistUser]

    def patch(self, request, playlist_id):
        playlist = get_object_or_404(
            Playlist.objects.filter(owner_id=request.user.id), id=playlist_id
        )
        track_ids = request.data.get("track_ids") if isinstance(request.data, dict) else None
        if (
            not isinstance(track_ids, list)
            or any(not isinstance(track_id, str) for track_id in track_ids)
        ):
            raise ValidationError(
                {"track_ids": "Provide an ordered list of track UUIDs."}
            )
        try:
            normalized_ids = [str(serializers.UUIDField().run_validation(value)) for value in track_ids]
        except ValidationError as error:
            raise ValidationError({"track_ids": "Every item must be a track UUID."}) from error
        if len(normalized_ids) != len(set(normalized_ids)):
            raise ValidationError({"track_ids": "Track UUIDs must not be repeated."})

        tracks = list(playlist.tracks.all())
        track_by_id = {str(track.id): track for track in tracks}
        if len(normalized_ids) != len(tracks) or set(normalized_ids) != set(track_by_id):
            raise ValidationError(
                {"track_ids": "Include every playlist track exactly once."}
            )

        with transaction.atomic():
            temporary_position = max(
                (track.position for track in tracks), default=-1
            ) + len(tracks) + 1
            for index, track in enumerate(tracks):
                track.position = temporary_position + index
                track.save(update_fields=["position"])
            for index, track_id in enumerate(normalized_ids):
                track = track_by_id[track_id]
                track.position = index
                track.save(update_fields=["position"])
        return Response(TrackSerializer(playlist.tracks.all(), many=True).data)


class FollowPlaylistView(APIView):
    permission_classes = [IsPlaylistUser]

    def post(self, request, playlist_id):
        playlist = get_object_or_404(
            Playlist.objects.filter(is_public=True), id=playlist_id
        )
        _, created = PlaylistFollow.objects.get_or_create(
            playlist=playlist, user_id=request.user.id
        )
        return Response(
            {"following": True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, playlist_id):
        playlist = get_object_or_404(
            Playlist.objects.filter(is_public=True), id=playlist_id
        )
        PlaylistFollow.objects.filter(
            playlist=playlist, user_id=request.user.id
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MostFollowedPlaylistsView(generics.ListAPIView):
    permission_classes = [IsPlaylistUser]
    serializer_class = PlaylistSerializer
    pagination_class = PlaylistPagination

    def get_queryset(self):
        return (
            Playlist.objects.filter(
                Q(is_public=True) | Q(owner_id=self.request.user.id)
            )
            .annotate(track_count=Count("tracks", distinct=True))
            .annotate(follower_count=Count("follows", distinct=True))
            .order_by("-follower_count", "name")
        )
