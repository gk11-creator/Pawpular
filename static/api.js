// ── API Communication ─────────────────────────────────────────────────────

const API_BASE = '';

async function apiFetch(method, path, body) {
  try {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' }
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API_BASE + path, opts);
    return { ok: res.ok, data: await res.json() };
  } catch {
    return {
      ok: false,
      data: { detail: 'Cannot reach server. Run: python server.py' }
    };
  }
}

async function apiGetLeaderboard(limit = 50) {
  return await apiFetch('GET', `/leaderboard?limit=${limit}`);
}

async function apiAddEntry(username, pet_name, pet_type, score, theme) {
  return await apiFetch('POST', '/add', { username, pet_name, pet_type, score, theme });
}

async function apiRemoveEntry(username) {
  return await apiFetch('DELETE', '/remove', { username });
}

async function apiGetInfo() {
  return await apiFetch('GET', '/info');
}

async function apiGetPerformance() {
  return await apiFetch('GET', '/performance');
}