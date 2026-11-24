from django.urls import path

from .views import (
    FollowPlaylistView,
    MostFollowedPlaylistsView,
    PlaylistDetailView,
    PlaylistListCreateView,
    PlaylistTrackListCreateView,
    ReorderTracksView,
    TrackDetailView,
)


urlpatterns = [
    path("playlists/", PlaylistListCreateView.as_view(), name="playlist-list"),
    path(
        "playlists/<uuid:playlist_id>/",
        PlaylistDetailView.as_view(),
        name="playlist-detail",
    ),
    path(
        "playlists/<uuid:playlist_id>/tracks/",
        PlaylistTrackListCreateView.as_view(),
        name="playlist-tracks",
    ),
    path(
        "playlists/<uuid:playlist_id>/tracks/reorder/",
        ReorderTracksView.as_view(),
        name="playlist-track-reorder",
    ),
    path("tracks/<uuid:track_id>/", TrackDetailView.as_view(), name="track-detail"),
    path(
        "playlists/<uuid:playlist_id>/follow/",
        FollowPlaylistView.as_view(),
        name="playlist-follow",
    ),
    path(
        "analytics/most-followed/",
        MostFollowedPlaylistsView.as_view(),
        name="most-followed-playlists",
    ),
]
