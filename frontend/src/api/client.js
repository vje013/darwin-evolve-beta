const API_BASE = window.location.hostname === 'localhost' ? '/api' : 'https://darwin-evolve-450665779990.us-central1.run.app'

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
// Graph Stats & Training Readiness
export const getGraphStats = () => request('/graph/stats')

export const getTrainingReadiness = () => request('/graph/training-readiness')

// Training
export const startTraining = () =>
  request('/graph/train', { method: 'POST' })

export const getTrainingStatus = (jobId) =>
  request(`/graph/train/${jobId}`)

export const listTrainedModels = () =>
  request('/graph/models')

// Vendr — Clinic Agent
export const analyzeClinicFeature = async (imageFile, featureFocus, specificQuestion) => {
  const formData = new FormData()
  formData.append('image', imageFile)
  formData.append('feature_focus', featureFocus)
  formData.append('specific_question', specificQuestion)

  const headers = {}
  if (getToken()) headers['Authorization'] = `Bearer ${getToken()}`

  const res = await fetch(`${API_BASE}/vendr/clinic/analyze`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (res.status === 401) { setToken(null); window.location.reload(); throw new Error('Unauthorized') }
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Failed') }
  return res.json()
}

export const getPersonas = () => request('/vendr/clinic/personas')

// Vendr — Research Agent
export const generateResearch = (query, maxPapers = 50) =>
  request('/vendr/research/generate', {
    method: 'POST',
    body: JSON.stringify({ query, max_papers: maxPapers }),
  })

// Vendr — Podcast Audio
export const generatePodcastAudio = (transcript, title) =>
  request('/vendr/research/podcast/generate-audio', {
    method: 'POST',
    body: JSON.stringify({ transcript, title }),
  })

// Vendr — Data Analyst
export const uploadDataset = async (file) => {
  const formData = new FormData()
  formData.append('file', file)

  const headers = {}
  if (getToken()) headers['Authorization'] = `Bearer ${getToken()}`

  const res = await fetch(`${API_BASE}/vendr/research/data/upload`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (res.status === 401) { setToken(null); window.location.reload(); throw new Error('Unauthorized') }
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Failed') }
  return res.json()
}

export const queryDataset = (dbId, query) =>
  request('/vendr/research/data/query', {
    method: 'POST',
    body: JSON.stringify({ db_id: dbId, query }),
  })

// Live Models
export const getLiveModels = () => request('/rooms/models/live')