const API_BASE = '/api'

let token = localStorage.getItem('darwin_token')

export function setToken(t) {
  token = t
  if (t) localStorage.setItem('darwin_token', t)
  else localStorage.removeItem('darwin_token')
}

export function getToken() {
  return token || localStorage.getItem('darwin_token')
}

async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  if (getToken()) {
    headers['Authorization'] = `Bearer ${getToken()}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    setToken(null)
    window.location.reload()
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }

  return res.json()
}

// Auth
export const register = (email, display_name, password) =>
  request('/register', { method: 'POST', body: JSON.stringify({ email, display_name, password }) })

export const login = (email, password) =>
  request('/login', { method: 'POST', body: JSON.stringify({ email, password }) })

export const getMe = () => request('/me')

// Rooms
export const createRoom = (name, description, default_model) =>
  request('/rooms', { method: 'POST', body: JSON.stringify({ name, description, default_model }) })

export const listRooms = () => request('/rooms')

export const getRoom = (roomId) => request(`/rooms/${roomId}`)

export const updateRoomSettings = (roomId, settings) =>
  request(`/rooms/${roomId}/settings`, { method: 'PUT', body: JSON.stringify(settings) })

export const listModels = () => request('/rooms/models')

// Members
export const addMember = (roomId, email, role) =>
  request(`/rooms/${roomId}/members`, { method: 'POST', body: JSON.stringify({ email, role }) })

// Messages
export const getMessages = (roomId, limit = 50) =>
  request(`/rooms/${roomId}/messages?limit=${limit}`)

export const sendMessage = (roomId, content, model_override = null) =>
  request(`/rooms/${roomId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content, model_override }),
  })

// Artifacts
export const generateArtifact = (roomId, artifact_type, instructions = '', model_override = null) =>
  request(`/rooms/${roomId}/artifacts/generate`, {
    method: 'POST',
    body: JSON.stringify({ artifact_type, instructions, model_override }),
  })

export const listArtifacts = (roomId) => request(`/rooms/${roomId}/artifacts`)

export const getArtifact = (roomId, artifactId) => request(`/rooms/${roomId}/artifacts/${artifactId}`)

// Connectors
export const addConnector = (roomId, connector_type, config) =>
  request(`/rooms/${roomId}/connectors`, {
    method: 'POST',
    body: JSON.stringify({ connector_type, config }),
  })

export const listConnectors = (roomId) => request(`/rooms/${roomId}/connectors`)

export const syncConnector = (roomId, connectorId) =>
  request(`/rooms/${roomId}/connectors/sync/${connectorId}`, { method: 'POST' })

export const syncAllConnectors = (roomId) =>
  request(`/rooms/${roomId}/connectors/sync-all`, { method: 'POST' })

export const removeConnector = (roomId, connectorId) =>
  request(`/rooms/${roomId}/connectors/connectors/${connectorId}`, { method: 'DELETE' })

export const listLinkedEntities = (roomId) => request(`/rooms/${roomId}/connectors/entities`)

export const getGraphData = (roomId) => request(`/rooms/${roomId}/connectors/graph`)

export const linkEntity = (roomId, entity_type, entity_id, name, url = '', attributes = {}) =>
  request(`/rooms/${roomId}/connectors/entities`, {
    method: 'POST',
    body: JSON.stringify({ entity_type, entity_id, name, url, attributes }),
  })

// Spend
export const getSpend = () => request('/spend')
