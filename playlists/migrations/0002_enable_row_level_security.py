from django.db import migrations


FORWARD_SQL = """
CREATE OR REPLACE FUNCTION public.current_playlist_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

ALTER TABLE playlists_playlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE playlists_playlist FORCE ROW LEVEL SECURITY;
CREATE POLICY playlist_read_access ON playlists_playlist
    FOR SELECT USING (is_public OR owner_id = public.current_playlist_user_id());
CREATE POLICY playlist_create_access ON playlists_playlist
    FOR INSERT WITH CHECK (owner_id = public.current_playlist_user_id());
CREATE POLICY playlist_update_access ON playlists_playlist
    FOR UPDATE
    USING (owner_id = public.current_playlist_user_id())
    WITH CHECK (owner_id = public.current_playlist_user_id());
CREATE POLICY playlist_delete_access ON playlists_playlist
    FOR DELETE USING (owner_id = public.current_playlist_user_id());

ALTER TABLE playlists_track ENABLE ROW LEVEL SECURITY;
ALTER TABLE playlists_track FORCE ROW LEVEL SECURITY;
CREATE POLICY track_read_access ON playlists_track
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM playlists_playlist AS playlist
            WHERE playlist.id = playlist_id
              AND (playlist.is_public OR playlist.owner_id = public.current_playlist_user_id())
        )
    );
CREATE POLICY track_create_access ON playlists_track
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM playlists_playlist AS playlist
            WHERE playlist.id = playlist_id
              AND playlist.owner_id = public.current_playlist_user_id()
        )
    );
CREATE POLICY track_update_access ON playlists_track
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM playlists_playlist AS playlist
            WHERE playlist.id = playlist_id
              AND playlist.owner_id = public.current_playlist_user_id()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM playlists_playlist AS playlist
            WHERE playlist.id = playlist_id
              AND playlist.owner_id = public.current_playlist_user_id()
        )
    );
CREATE POLICY track_delete_access ON playlists_track
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM playlists_playlist AS playlist
            WHERE playlist.id = playlist_id
              AND playlist.owner_id = public.current_playlist_user_id()
        )
    );

ALTER TABLE playlists_playlistfollow ENABLE ROW LEVEL SECURITY;
ALTER TABLE playlists_playlistfollow FORCE ROW LEVEL SECURITY;
CREATE POLICY follow_read_access ON playlists_playlistfollow
    FOR SELECT USING (
        user_id = public.current_playlist_user_id()
        OR EXISTS (
            SELECT 1 FROM playlists_playlist AS playlist
            WHERE playlist.id = playlist_id
              AND (playlist.is_public OR playlist.owner_id = public.current_playlist_user_id())
        )
    );
CREATE POLICY follow_create_access ON playlists_playlistfollow
    FOR INSERT WITH CHECK (
        user_id = public.current_playlist_user_id()
        AND EXISTS (
            SELECT 1 FROM playlists_playlist AS playlist
            WHERE playlist.id = playlist_id AND playlist.is_public
        )
    );
CREATE POLICY follow_delete_access ON playlists_playlistfollow
    FOR DELETE USING (user_id = public.current_playlist_user_id());
"""

REVERSE_SQL = """
DROP POLICY IF EXISTS follow_delete_access ON playlists_playlistfollow;
DROP POLICY IF EXISTS follow_create_access ON playlists_playlistfollow;
DROP POLICY IF EXISTS follow_read_access ON playlists_playlistfollow;
DROP POLICY IF EXISTS track_delete_access ON playlists_track;
DROP POLICY IF EXISTS track_update_access ON playlists_track;
DROP POLICY IF EXISTS track_create_access ON playlists_track;
DROP POLICY IF EXISTS track_read_access ON playlists_track;
DROP POLICY IF EXISTS playlist_delete_access ON playlists_playlist;
DROP POLICY IF EXISTS playlist_update_access ON playlists_playlist;
DROP POLICY IF EXISTS playlist_create_access ON playlists_playlist;
DROP POLICY IF EXISTS playlist_read_access ON playlists_playlist;
ALTER TABLE playlists_playlistfollow DISABLE ROW LEVEL SECURITY;
ALTER TABLE playlists_track DISABLE ROW LEVEL SECURITY;
ALTER TABLE playlists_playlist DISABLE ROW LEVEL SECURITY;
DROP FUNCTION IF EXISTS public.current_playlist_user_id();
"""


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(FORWARD_SQL)


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    dependencies = [("playlists", "0001_initial")]
    operations = [migrations.RunPython(enable_rls, disable_rls)]
