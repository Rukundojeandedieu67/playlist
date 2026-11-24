import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const config = window.APP_CONFIG || {};
const apiBaseUrl = (config.apiBaseUrl || "").replace(/\/$/, "");
const supabase = config.supabaseUrl && config.supabaseAnonKey
  ? createClient(config.supabaseUrl, config.supabaseAnonKey)
  : null;

const elements = {
  authPanel: document.querySelector("#auth-panel"),
  appPanel: document.querySelector("#app-panel"),
  accountLabel: document.querySelector("#account-label"),
  signout: document.querySelector("#signout-button"),
  authForm: document.querySelector("#auth-form"),
  authHeading: document.querySelector("#auth-heading"),
  authEmail: document.querySelector("#auth-email"),
  authPassword: document.querySelector("#auth-password"),
  authSubmit: document.querySelector("#auth-submit"),
  authMode: document.querySelector("#auth-mode"),
  authMessage: document.querySelector("#auth-message"),
  homeView: document.querySelector("#home-view"),
  detailView: document.querySelector("#detail-view"),
  analyticsView: document.querySelector("#analytics-view"),
  playlistGrid: document.querySelector("#playlist-grid"),
  homeMessage: document.querySelector("#home-message"),
  pagination: document.querySelector("#pagination"),
  showCreate: document.querySelector("#show-create"),
  createForm: document.querySelector("#create-form"),
  cancelCreate: document.querySelector("#cancel-create"),
  playlistName: document.querySelector("#playlist-name"),
  playlistPublic: document.querySelector("#playlist-public"),
  detailContent: document.querySelector("#detail-content"),
  analyticsGrid: document.querySelector("#analytics-grid"),
  analyticsMessage: document.querySelector("#analytics-message")
};

let isSignup = false;
let currentPage = 1;
let currentUser = null;

function showNotice(element, message = "", kind = "") {
  element.textContent = message;
  element.className = `notice ${kind}`.trim();
}

async function getAccessToken() {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || null;
}

async function api(path, options = {}) {
  const token = await getAccessToken();
  const response = await fetch(`${apiBaseUrl}/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers
    }
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail || Object.values(body).flat().join(" ") || "Request failed.";
    const error = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    error.status = response.status;
    throw error;
  }
  return body;
}

function playlistCard(playlist) {
  const card = document.createElement("article");
  card.className = "playlist-card";
  card.innerHTML = `
    <a href="#playlist/${playlist.id}" aria-label="Open ${escapeHtml(playlist.name)}">
      <div class="card-art" aria-hidden="true">♫</div>
      <h3>${escapeHtml(playlist.name)}</h3>
    </a>
    <p class="card-meta">${playlist.track_count} tracks · ${playlist.follower_count} followers</p>
    <div class="card-actions">
      <span class="badge">${playlist.is_public ? "PUBLIC" : "PRIVATE"}</span>
      ${playlist.is_public && playlist.owner_id !== currentUser.id
        ? `<button class="text-button follow-button" data-id="${playlist.id}">Follow</button>`
        : `<a class="text-button" href="#playlist/${playlist.id}">Open mix →</a>`}
    </div>`;
  card.querySelector(".follow-button")?.addEventListener("click", async (event) => {
    event.preventDefault();
    try {
      await api(`/playlists/${playlist.id}/follow/`, { method: "POST" });
      event.currentTarget.textContent = "Following";
      event.currentTarget.disabled = true;
    } catch (error) {
      showNotice(elements.homeMessage, error.message, "error");
    }
  });
  return card;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function renderCards(container, playlists, emptyMessage) {
  container.replaceChildren();
  if (!playlists.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = emptyMessage;
    container.append(empty);
    return;
  }
  playlists.forEach((playlist) => container.append(playlistCard(playlist)));
}

async function loadPlaylists(page = 1) {
  currentPage = page;
  elements.playlistGrid.innerHTML = '<div class="empty-state">Loading playlists…</div>';
  showNotice(elements.homeMessage);
  try {
    const result = await api(`/playlists/?page=${page}`);
    renderCards(elements.playlistGrid, result.results, "No playlists yet. Create the first one.");
    elements.pagination.replaceChildren();
    if (result.previous) {
      const previous = document.createElement("button");
      previous.className = "button button-quiet";
      previous.textContent = "← Previous";
      previous.addEventListener("click", () => loadPlaylists(page - 1));
      elements.pagination.append(previous);
    }
    if (result.next) {
      const next = document.createElement("button");
      next.className = "button button-quiet";
      next.textContent = "Next →";
      next.addEventListener("click", () => loadPlaylists(page + 1));
      elements.pagination.append(next);
    }
  } catch (error) {
    elements.playlistGrid.replaceChildren();
    showNotice(elements.homeMessage, error.message, "error");
  }
}

function makeTrackRow(track, index, isOwner) {
  const row = document.createElement("li");
  row.className = "track-row";
  row.draggable = isOwner;
  row.dataset.id = track.id;
  row.innerHTML = `
    <span class="track-number">${String(index + 1).padStart(2, "0")}</span>
    <span class="track-title">${escapeHtml(track.title)}</span>
    <a class="track-link" href="${escapeHtml(track.url)}" target="_blank" rel="noopener noreferrer">Listen ↗</a>
    ${isOwner ? `<button class="text-button remove-track" type="button" aria-label="Remove ${escapeHtml(track.title)}">Remove</button>` : ""}`;
  row.querySelector(".remove-track")?.addEventListener("click", async () => {
    try {
      await api(`/tracks/${track.id}/`, { method: "DELETE" });
      await loadDetail(location.hash.split("/")[1]);
    } catch (error) {
      showNotice(elements.detailContent.querySelector(".notice"), error.message, "error");
    }
  });
  return row;
}

async function loadDetail(id) {
  elements.detailContent.innerHTML = '<div class="empty-state">Loading playlist…</div>';
  try {
    const playlist = await api(`/playlists/${id}/`);
    const tracks = await api(`/playlists/${id}/tracks/`);
    const isOwner = playlist.owner_id === currentUser.id;
    elements.detailContent.replaceChildren();

    const header = document.createElement("div");
    header.className = "detail-header";
    header.innerHTML = `
      <div><p class="eyebrow">${playlist.is_public ? "Public playlist" : "Private playlist"}</p>
      <h2>${escapeHtml(playlist.name)}</h2>
      <p class="detail-description">${tracks.length} tracks · ${playlist.follower_count} followers</p></div>
      ${isOwner ? `<button class="button button-quiet toggle-visibility">${playlist.is_public ? "Make private" : "Make public"}</button>` : ""}`;
    header.querySelector(".toggle-visibility")?.addEventListener("click", async () => {
      try {
        await api(`/playlists/${id}/`, {
          method: "PATCH",
          body: JSON.stringify({ is_public: !playlist.is_public })
        });
        await loadDetail(id);
      } catch (error) {
        showNotice(elements.detailContent.querySelector(".notice"), error.message, "error");
      }
    });
    elements.detailContent.append(header);

    const trackHeading = document.createElement("div");
    trackHeading.className = "track-heading";
    trackHeading.innerHTML = `<h3>Track list</h3><span class="muted">${isOwner ? "Drag tracks to change the order" : "In listening order"}</span>`;
    elements.detailContent.append(trackHeading);

    const list = document.createElement("ol");
    list.className = "track-list";
    tracks.forEach((track, index) => list.append(makeTrackRow(track, index, isOwner)));
    if (!tracks.length) {
      const empty = document.createElement("li");
      empty.className = "empty-state";
      empty.textContent = "This playlist is waiting for its first track.";
      list.append(empty);
    }
    if (isOwner) setupReordering(list, id);
    elements.detailContent.append(list);

    const notice = document.createElement("p");
    notice.className = "notice";
    notice.setAttribute("role", "status");
    elements.detailContent.append(notice);

    if (isOwner) {
      const form = document.createElement("form");
      form.className = "track-form";
      form.innerHTML = `
        <label>Track title<input name="title" maxlength="200" required placeholder="Song title"></label>
        <label>Link<input name="url" type="url" maxlength="2048" required placeholder="https://…"></label>
        <button class="button button-primary" type="submit">Add track</button>`;
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const values = new FormData(form);
        try {
          await api(`/playlists/${id}/tracks/`, {
            method: "POST",
            body: JSON.stringify({ title: values.get("title"), url: values.get("url") })
          });
          await loadDetail(id);
        } catch (error) {
          showNotice(notice, error.message, "error");
        }
      });
      elements.detailContent.append(form);
      const removePlaylist = document.createElement("button");
      removePlaylist.className = "text-button";
      removePlaylist.textContent = "Delete playlist";
      removePlaylist.addEventListener("click", async () => {
        if (!window.confirm("Delete this playlist and all its tracks?")) return;
        try {
          await api(`/playlists/${id}/`, { method: "DELETE" });
          location.hash = "#home";
        } catch (error) {
          showNotice(notice, error.message, "error");
        }
      });
      elements.detailContent.append(removePlaylist);
    }
  } catch (error) {
    elements.detailContent.innerHTML = "";
    const message = document.createElement("div");
    message.className = "empty-state";
    message.textContent = error.status === 404
      ? "Playlist not found, or it is private and you do not have access."
      : error.message;
    elements.detailContent.append(message);
  }
}

function setupReordering(list, playlistId) {
  let dragged = null;
  list.addEventListener("dragstart", (event) => {
    const row = event.target.closest(".track-row");
    if (!row) return;
    dragged = row;
    row.classList.add("dragging");
    event.dataTransfer.effectAllowed = "move";
  });
  list.addEventListener("dragend", () => {
    dragged?.classList.remove("dragging");
    list.querySelectorAll(".drag-over").forEach((row) => row.classList.remove("drag-over"));
    dragged = null;
  });
  list.addEventListener("dragover", (event) => {
    event.preventDefault();
    const target = event.target.closest(".track-row");
    if (!target || target === dragged) return;
    target.classList.add("drag-over");
    const bounds = target.getBoundingClientRect();
    list.insertBefore(dragged, event.clientY < bounds.top + bounds.height / 2 ? target : target.nextSibling);
  });
  list.addEventListener("dragleave", (event) => event.target.closest(".track-row")?.classList.remove("drag-over"));
  list.addEventListener("drop", async (event) => {
    event.preventDefault();
    list.querySelectorAll(".drag-over").forEach((row) => row.classList.remove("drag-over"));
    const notice = elements.detailContent.querySelector(".notice");
    const trackIds = [...list.querySelectorAll(".track-row")].map((row) => row.dataset.id);
    try {
      await api(`/playlists/${playlistId}/tracks/reorder/`, {
        method: "PATCH",
        body: JSON.stringify({ track_ids: trackIds })
      });
      showNotice(notice, "Track order saved.", "success");
      [...list.querySelectorAll(".track-number")].forEach((number, index) => {
        number.textContent = String(index + 1).padStart(2, "0");
      });
    } catch (error) {
      showNotice(notice, error.message, "error");
      await loadDetail(playlistId);
    }
  });
}

async function loadAnalytics() {
  elements.analyticsGrid.innerHTML = '<div class="empty-state">Loading favorites…</div>';
  try {
    const result = await api("/analytics/most-followed/");
    renderCards(elements.analyticsGrid, result.results, "No followed playlists yet.");
  } catch (error) {
    elements.analyticsGrid.replaceChildren();
    showNotice(elements.analyticsMessage, error.message, "error");
  }
}

function renderRoute() {
  const route = location.hash.slice(1) || "home";
  elements.homeView.hidden = route !== "home";
  elements.detailView.hidden = !route.startsWith("playlist/");
  elements.analyticsView.hidden = route !== "analytics";
  if (route === "home") loadPlaylists(currentPage);
  else if (route === "analytics") loadAnalytics();
  else if (route.startsWith("playlist/")) loadDetail(route.split("/")[1]);
}

function setAuthenticated(session) {
  currentUser = session?.user || null;
  elements.authPanel.hidden = Boolean(session);
  elements.appPanel.hidden = !session;
  elements.signout.hidden = !session;
  elements.accountLabel.textContent = session?.user?.email || "Signed out";
  if (session) renderRoute();
}

elements.authMode.addEventListener("click", () => {
  isSignup = !isSignup;
  elements.authHeading.textContent = isSignup ? "Create your account" : "Welcome back";
  elements.authSubmit.textContent = isSignup ? "Sign up" : "Sign in";
  elements.authMode.textContent = isSignup ? "Already a member? Sign in" : "New here? Create an account";
  elements.authPassword.autocomplete = isSignup ? "new-password" : "current-password";
  showNotice(elements.authMessage);
});

elements.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!supabase) {
    showNotice(elements.authMessage, "Add your Supabase URL and anon key to frontend/public/config.js.", "error");
    return;
  }
  showNotice(elements.authMessage, isSignup ? "Creating your account…" : "Signing in…");
  const credentials = {
    email: elements.authEmail.value,
    password: elements.authPassword.value
  };
  const result = isSignup
    ? await supabase.auth.signUp(credentials)
    : await supabase.auth.signInWithPassword(credentials);
  if (result.error) {
    showNotice(elements.authMessage, result.error.message, "error");
    return;
  }
  if (isSignup && !result.data.session) {
    showNotice(elements.authMessage, "Check your email to confirm your account, then sign in.", "success");
    return;
  }
  setAuthenticated(result.data.session);
});

elements.signout.addEventListener("click", async () => {
  const { error } = await supabase.auth.signOut();
  if (error) showNotice(elements.homeMessage, error.message, "error");
  else setAuthenticated(null);
});

elements.showCreate.addEventListener("click", () => {
  elements.createForm.hidden = !elements.createForm.hidden;
  if (!elements.createForm.hidden) elements.playlistName.focus();
});
elements.cancelCreate.addEventListener("click", () => { elements.createForm.hidden = true; });
elements.createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const playlist = await api("/playlists/", {
      method: "POST",
      body: JSON.stringify({
        name: elements.playlistName.value,
        is_public: elements.playlistPublic.checked
      })
    });
    elements.createForm.reset();
    elements.createForm.hidden = true;
    location.hash = `#playlist/${playlist.id}`;
  } catch (error) {
    showNotice(elements.homeMessage, error.message, "error");
  }
});

window.addEventListener("hashchange", renderRoute);

if (!supabase || !apiBaseUrl) {
  showNotice(elements.authMessage, "Set Supabase and API settings in config.js before using the app.", "error");
  elements.accountLabel.textContent = "Setup required";
  elements.authPanel.hidden = false;
} else {
  supabase.auth.getSession().then(({ data: { session } }) => setAuthenticated(session));
  supabase.auth.onAuthStateChange((_event, session) => setAuthenticated(session));
}
