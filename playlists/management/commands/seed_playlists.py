import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from playlists.middleware import set_database_claims
from playlists.models import Playlist, Track


SEED_OWNER_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SAMPLE_PLAYLISTS = [
    {
        "name": "Soft Start",
        "is_public": True,
        "tracks": [
            ("First Light", "https://example.com/tracks/first-light"),
            ("Window Seat", "https://example.com/tracks/window-seat"),
            ("Slow Sunday", "https://example.com/tracks/slow-sunday"),
            ("Coffee Break", "https://example.com/tracks/coffee-break"),
        ],
    },
    {
        "name": "After Hours",
        "is_public": False,
        "tracks": [
            ("Neon Street", "https://example.com/tracks/neon-street"),
            ("Last Train", "https://example.com/tracks/last-train"),
            ("Night Drive", "https://example.com/tracks/night-drive"),
            ("Home Again", "https://example.com/tracks/home-again"),
        ],
    },
]


class Command(BaseCommand):
    help = "Create two sample playlists and eight tracks (ten rows total)."

    def handle(self, *args, **options):
        with transaction.atomic():
            set_database_claims(str(SEED_OWNER_ID))
            for sample in SAMPLE_PLAYLISTS:
                playlist, _ = Playlist.objects.get_or_create(
                    owner_id=SEED_OWNER_ID,
                    name=sample["name"],
                    defaults={"is_public": sample["is_public"]},
                )
                for position, (title, url) in enumerate(sample["tracks"]):
                    Track.objects.get_or_create(
                        playlist=playlist,
                        title=title,
                        defaults={"url": url, "position": position},
                    )
        self.stdout.write(self.style.SUCCESS("Seeded 2 playlists and 8 tracks."))
