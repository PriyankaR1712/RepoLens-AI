const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error('Could not reach the RepoLens API. Check that the backend is running and try again.');
  }

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json().catch(() => null)
    : await response.text().catch(() => '');

  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === 'string'
      ? detail
      : detail?.message || (typeof payload === 'string' ? payload : null);
    const error = new Error(message || `Request failed with status ${response.status}.`);
    error.status = response.status;
    error.detail = detail;
    throw error;
  }

  return payload;
}

export const api = {
  health: () => request('/health'),
  repositories: () => request('/repositories/'),
  repository: (id) => request(`/repositories/${id}`),
  ingest: (sourceUrl) => request('/repositories/ingest', {
    method: 'POST',
    body: JSON.stringify({ source_url: sourceUrl }),
  }),
  index: (id) => request(`/repositories/${id}/index`, { method: 'POST' }),
  ask: (id, question) => request(`/repositories/${id}/ask`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  }),
};
