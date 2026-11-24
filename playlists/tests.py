import uuid
from time import time

import jwt
from rest_framework.test import APIClient, APITestCase

from .authentication import SupabaseUser
from .models import Playlist, Track


class PlaylistAPITests(APITestCase):
    def setUp(self):
        self.owner_id = uuid.uuid4()
        self.other_id = uuid.uuid4()
        self.playlist = Playlist.objects.create(
            name="Public mix", is_public=True, owner_id=self.owner_id
        )
        self.client.force_authenticate(
            user=SupabaseUser(str(self.owner_id), "user", {})
        )

    def make_token(self, role="user", secret="test-signing-key-at-least-32-bytes"):
        return jwt.encode(
            {
                "sub": str(self.owner_id),
                "role": "authenticated",
                "app_metadata": {"role": role},
                "aud": "authenticated",
                "iss": "https://project.supabase.co/auth/v1",
                "exp": int(time()) + 60,
            },
            secret,
            algorithm="HS256",
        )

    def test_list_returns_public_and_owned_playlists(self):
        response = self.client.get("/api/playlists/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_create_rejects_missing_playlist_name(self):
        response = self.client.post(
            "/api/playlists/", {"is_public": True}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Playlist.objects.filter(owner_id=self.owner_id).count(), 1)

    def test_private_playlist_is_hidden_from_another_user(self):
        private_playlist = Playlist.objects.create(
            name="Secret mix", is_public=False, owner_id=self.owner_id
        )
        self.client.force_authenticate(
            user=SupabaseUser(str(self.other_id), "user", {})
        )
        response = self.client.get(f"/api/playlists/{private_playlist.id}/")
        self.assertEqual(response.status_code, 404)

    def test_wrong_role_is_denied(self):
        client = APIClient()
        with self.settings(
            SUPABASE_JWT_SECRET="test-signing-key-at-least-32-bytes",
            SUPABASE_JWT_ISSUER="https://project.supabase.co/auth/v1",
        ):
            client.credentials(
                HTTP_AUTHORIZATION=f"Bearer {self.make_token(role='admin')}"
            )
            response = client.get("/api/playlists/")
        self.assertEqual(response.status_code, 403)

    def test_signed_supabase_token_authenticates(self):
        client = APIClient()
        with self.settings(
            SUPABASE_JWT_SECRET="test-signing-key-at-least-32-bytes",
            SUPABASE_JWT_ISSUER="https://project.supabase.co/auth/v1",
        ):
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.make_token()}")
            response = client.get("/api/playlists/")
        self.assertEqual(response.status_code, 200)

    def test_reorder_updates_track_positions(self):
        first = Track.objects.create(
            playlist=self.playlist,
            title="First",
            url="https://example.com/first",
            position=0,
        )
        second = Track.objects.create(
            playlist=self.playlist,
            title="Second",
            url="https://example.com/second",
            position=1,
        )
        response = self.client.patch(
            f"/api/playlists/{self.playlist.id}/tracks/reorder/",
            {"track_ids": [str(second.id), str(first.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(
                self.playlist.tracks.order_by("position").values_list(
                    "id", flat=True
                )
            ),
            [second.id, first.id],
        )

    def test_reorder_rejects_an_incomplete_track_list(self):
        Track.objects.create(
            playlist=self.playlist,
            title="First",
            url="https://example.com/first",
            position=0,
        )
        response = self.client.patch(
            f"/api/playlists/{self.playlist.id}/tracks/reorder/",
            {"track_ids": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
