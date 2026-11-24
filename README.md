# Mixtape: playlist sharing

A playlist-sharing app with a Django REST API, Supabase Auth/Postgres, and a static HTML/CSS/JavaScript frontend. The frontend is deployed on Netlify and the API on Render.

## What works

- Supabase email/password sign-up and sign-in; Django verifies each Supabase access token.
- Public playlists and the signed-in user's own private playlists; another user receives `404` for a private playlist.
- Playlist and track create/read/update/delete API operations, zero-based track positions, and drag-to-reorder.
- Follow/unfollow and a paginated most-followed endpoint.
- Django role checks (`authenticated` Supabase token, `user` app role), ownership checks, request validation, and Postgres row-level security.
- Seven API tests, including signed-token authentication, private visibility, role rejection, invalid input, and reorder behavior.

## Run locally

Requirements: Python 3.11+, Node.js 20+, PostgreSQL 17+, and a Supabase project. SQLite can be used temporarily for API-only tests.

1. Create a Supabase project and enable Email sign-up in **Authentication → Providers**. Copy its Project URL, anon/public key, and JWT secret from **Project Settings → API**.
2. In PowerShell, from the project root:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

3. In pgAdmin, connect to your local PostgreSQL server, right-click **Databases → Create → Database**, create a database named `mixtape`, and use the login role for your local server as its owner. Set that role's password in your local `.env` `DATABASE_URL` (URL-encode any special characters in the password); do not paste it into chat or commit `.env`. Then set `SUPABASE_URL` and, for legacy HS256 tokens, `SUPABASE_JWT_SECRET` in `.env`:

   ```powershell
   $env:DJANGO_SECRET_KEY = "use-a-long-random-value"
   $env:DJANGO_DEBUG = "true"
   $env:SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
   $env:SUPABASE_JWT_SECRET = "YOUR_PROJECT_JWT_SECRET"
   $env:DATABASE_URL = "postgresql://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/mixtape"
   $env:FRONTEND_ORIGINS = "http://localhost:8001,http://127.0.0.1:8001"
   ```

   `SUPABASE_JWKS_URL` and `SUPABASE_JWT_ISSUER` default from `SUPABASE_URL`. New Supabase projects that issue asymmetric JWTs use the JWKS endpoint; the JWT secret is needed only for legacy HS256 tokens. Do not expose the JWT secret or database URL in frontend code. To temporarily run API-only tests on SQLite, set `DATABASE_URL=sqlite:///db.sqlite3`.
4. Run Django migrations, optionally load the ten sample database rows, and start the API:

   ```powershell
   python manage.py migrate
   python manage.py seed_playlists
   python manage.py runserver
   ```

   The seed command inserts two playlists and eight tracks. It is safe to run again.
5. In `frontend\public\config.js`, set `apiBaseUrl` to `http://127.0.0.1:8000`, and set the Supabase project URL and anon/public key. Open `frontend\public\index.html` through a local static server (not `file://`):

   ```powershell
   python -m http.server 8001 --directory frontend\public
   ```

   Visit `http://127.0.0.1:8001`. Add this origin to Supabase Auth's allowed redirect URLs for local sign-up confirmation.
6. Run the tests with `python manage.py test`.

The API is rooted at `/api/`. Authenticated requests send `Authorization: Bearer <Supabase access token>`.

### Curl walkthrough (PowerShell)

Sign in through the app and copy the access token from the browser's Supabase session, then set the two values below. The anon key is public; do not use a Supabase service-role key.

```powershell
$env:API = "http://127.0.0.1:8000"
$env:TOKEN = "PASTE_A_TEST_USER_ACCESS_TOKEN"
curl.exe -i "$env:API/api/playlists/" -H "Authorization: Bearer $env:TOKEN"
curl.exe -i -X POST "$env:API/api/playlists/" -H "Authorization: Bearer $env:TOKEN" -H "Content-Type: application/json" -d '{"name":"Road trip","is_public":true}'
```

Copy the returned playlist ID and track IDs to test adding and reordering tracks:

```powershell
$env:PLAYLIST_ID = "PASTE_PLAYLIST_UUID"
curl.exe -i -X POST "$env:API/api/playlists/$env:PLAYLIST_ID/tracks/" -H "Authorization: Bearer $env:TOKEN" -H "Content-Type: application/json" -d '{"title":"First song","url":"https://example.com/first-song"}'
curl.exe -i -X PATCH "$env:API/api/playlists/$env:PLAYLIST_ID/tracks/reorder/" -H "Authorization: Bearer $env:TOKEN" -H "Content-Type: application/json" -d '{"track_ids":["TRACK_UUID_1","TRACK_UUID_2"]}'
curl.exe -i "$env:API/api/analytics/most-followed/" -H "Authorization: Bearer $env:TOKEN"
```

The reorder request must include every track UUID in the playlist exactly once. `curl.exe -i` prints the status line so you can verify success (`200`), invalid input (`400`), missing/private (`404`), and wrong role (`403`).

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `/api/playlists/` | List visible playlists (paginated) or create one |
| GET, PATCH, DELETE | `/api/playlists/{id}/` | Read, update, or delete an owned playlist |
| GET, POST | `/api/playlists/{id}/tracks/` | List or add tracks |
| PATCH | `/api/playlists/{id}/tracks/reorder/` | Set order with `{"track_ids":["uuid", "..."]}` |
| PATCH, DELETE | `/api/tracks/{id}/` | Update or remove an owned track |
| POST, DELETE | `/api/playlists/{id}/follow/` | Follow or unfollow a public playlist |
| GET | `/api/analytics/most-followed/` | Paginated most-followed visible playlists |
| GET | `/api/health/` | Render health check |

List responses use the standard paginated shape (`count`, `next`, `previous`, `results`). Track positions start at `0`. Bad input returns `400`; missing or inaccessible records return `404`; an authenticated account with a non-`user` app role receives `403`.

## Supabase database and RLS

`python manage.py migrate` enables and forces RLS on the playlist, track, and follow tables in PostgreSQL. Django sets the verified user's subject with transaction-local Postgres settings before API queries. SQLite skips RLS and is intended only for local tests.

Use a dedicated Supabase database login for `DATABASE_URL` that does **not** have `BYPASSRLS`; keep it as the table owner so Django migrations can create/update tables. The migration forces RLS even for table owners. Do not use the Supabase service-role key or a privileged database login as the public API's data-access mechanism. The API's ownership and visibility checks remain in place as a second boundary.

## Deploy in phases

### Phase 1 — Supabase

1. Create the Supabase project and enable email/password auth.
2. Configure allowed redirect URLs for your eventual Netlify site URL.
3. Create a database login without `BYPASSRLS`, and use its PostgreSQL connection string as the Render `DATABASE_URL`. Keep credentials private.
4. Obtain the project URL, anon/public key, and, for legacy HS256 tokens, the JWT secret. The anon/public key is expected in the browser; the JWT secret and database URL are server-only.

### Phase 2 — Django on Render

1. Push this project to a Git provider and create a Render **Blueprint** from `render.yaml` (or create a Python web service with the same commands).
2. Set `DATABASE_URL`, `SUPABASE_URL`, `FRONTEND_ORIGINS`, and `SUPABASE_JWT_SECRET` if your Supabase project uses HS256. For asymmetric JWTs, set `SUPABASE_JWKS_URL` only if you use a non-default JWKS URL. Set `DJANGO_ALLOWED_HOSTS` to the Render API hostname.
3. Deploy. The start command runs migrations before Gunicorn starts; verify `/api/health/` returns `{"status":"ok"}`.

### Phase 3 — HTML/CSS/JS on Netlify

1. Import the same repository into Netlify. `netlify.toml` configures the `frontend` base directory and static build.
2. Set these Netlify environment variables: `API_BASE_URL` (Render origin, no `/api` suffix), `SUPABASE_URL`, and `SUPABASE_ANON_KEY`. The build writes them to the generated `config.js`; never put server secrets there.
3. After the first deploy, set Render's `FRONTEND_ORIGINS` to the exact Netlify origin and redeploy the API. Add the Netlify site URL to Supabase Auth's allowed redirect URLs.
4. Sign up two test accounts. Create a private playlist as the first user and open its URL as the second; the API must return `404` with a clear private-playlist message. Reorder tracks and confirm the screen updates only after the API accepts the new order.

## Partner exercise

Use the API paths and bearer-token format above for the curl walkthrough. The reorder flow is: **browser drag event → `PATCH /tracks/reorder/` with ordered IDs → Django authenticates/authorizes and persists positions → `200` with reordered tracks → browser redraws the list**. On a rejected request, the screen shows the API message; missing/private playlists return `404`, invalid order data returns `400`, and wrong roles return `403`.
# playlist
