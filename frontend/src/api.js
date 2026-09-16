const BASE = '/api/v1'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  if (!res.ok) {
    let detail
    try {
      detail = await res.json()
    } catch {
      detail = await res.text()
    }
    const err = new Error(
      typeof detail === 'string' ? detail : JSON.stringify(detail),
    )
    err.status = res.status
    err.detail = detail
    throw err
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  getStatus: () => request('/status'),
  list: () => request('/cover-letters'),
  get: (id) => request(`/cover-letters/${id}`),
  create: (body) => request('/cover-letters', { method: 'POST', body }),
  update: (id, body) =>
    request(`/cover-letters/${id}`, { method: 'PUT', body }),
  remove: (id) => request(`/cover-letters/${id}`, { method: 'DELETE' }),
  regenerate: (id) =>
    request(`/cover-letters/${id}/regenerate`, { method: 'POST' }),
  pdfUrl: (id) => `${BASE}/cover-letters/${id}/pdf`,
}
