import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Button, TextField, Chip, IconButton, Dialog, DialogTitle,
  DialogContent, DialogActions, Select, MenuItem, FormControl, InputLabel,
  CircularProgress, Paper, Tooltip, Divider, Alert,
} from '@mui/material'
import GitHubIcon from '@mui/icons-material/GitHub'
import BrushIcon from '@mui/icons-material/Brush'
import ViewKanbanIcon from '@mui/icons-material/ViewKanban'
import SyncIcon from '@mui/icons-material/Sync'
import AddIcon from '@mui/icons-material/Add'
import LinkIcon from '@mui/icons-material/Link'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import CodeIcon from '@mui/icons-material/Code'
import BugReportIcon from '@mui/icons-material/BugReport'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import {
  addConnector, listConnectors, syncConnector, syncAllConnectors,
  listLinkedEntities, removeConnector,
} from '../api/client'

const ENTITY_ICONS = {
  Repository: <CodeIcon sx={{ fontSize: '0.9rem' }} />,
  PullRequest: <AccountTreeIcon sx={{ fontSize: '0.9rem' }} />,
  Issue: <BugReportIcon sx={{ fontSize: '0.9rem' }} />,
  Commit: <CodeIcon sx={{ fontSize: '0.9rem' }} />,
  FigmaFile: <BrushIcon sx={{ fontSize: '0.9rem' }} />,
  FigmaPage: <BrushIcon sx={{ fontSize: '0.9rem' }} />,
  FigmaFrame: <BrushIcon sx={{ fontSize: '0.9rem' }} />,
  FigmaComponent: <BrushIcon sx={{ fontSize: '0.9rem' }} />,
  Task: <ViewKanbanIcon sx={{ fontSize: '0.9rem' }} />,
  Requirement: <AccountTreeIcon sx={{ fontSize: '0.9rem' }} />,
  Person: <LinkIcon sx={{ fontSize: '0.9rem' }} />,
  Decision: <LinkIcon sx={{ fontSize: '0.9rem' }} />,
  Component: <BrushIcon sx={{ fontSize: '0.9rem' }} />,
  System: <CodeIcon sx={{ fontSize: '0.9rem' }} />,
}

const SOURCE_COLORS = {
  github: '#238636',
  figma: '#a259ff',
  trello: '#0079bf',
  chat_extraction: 'rgba(110, 231, 183, 0.3)',
}

const CONNECTOR_ICONS = {
  github: <GitHubIcon sx={{ fontSize: '0.8rem' }} />,
  figma: <BrushIcon sx={{ fontSize: '0.8rem' }} />,
  trello: <ViewKanbanIcon sx={{ fontSize: '0.8rem' }} />,
}

export default function ConnectorsPanel({ roomId }) {
  const [connectors, setConnectors] = useState([])
  const [entities, setEntities] = useState([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [connectorType, setConnectorType] = useState('github')
  const [githubRepo, setGithubRepo] = useState('')
  const [githubToken, setGithubToken] = useState('')
  const [figmaFileKey, setFigmaFileKey] = useState('')
  const [figmaToken, setFigmaToken] = useState('')
  const [trelloBoardId, setTrelloBoardId] = useState('')
  const [trelloToken, setTrelloToken] = useState('')
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState(null)
  const [error, setError] = useState('')
  const [filterSource, setFilterSource] = useState('all')

  const load = async () => {
    try {
      const [c, e] = await Promise.all([
        listConnectors(roomId),
        listLinkedEntities(roomId),
      ])
      setConnectors(c)
      setEntities(e)
    } catch (err) {
      console.error('Load error:', err)
    }
  }

  useEffect(() => { load() }, [roomId])

  const handleAddConnector = async () => {
    setError('')
    setLoading(true)
    try {
      let config = {}
      if (connectorType === 'github') {
        if (!githubRepo || !githubToken) { setError('Repo and token required'); setLoading(false); return }
        config = { repo: githubRepo, token: githubToken }
      } else if (connectorType === 'figma') {
        if (!figmaFileKey || !figmaToken) { setError('File key and token required'); setLoading(false); return }
        config = { file_key: figmaFileKey, token: figmaToken }
      } else if (connectorType === 'trello') {
        if (!trelloBoardId || !trelloToken) { setError('Board ID and token required'); setLoading(false); return }
        config = { board_id: trelloBoardId, token: trelloToken }
      }

      const result = await addConnector(roomId, connectorType, config)
      setSyncResult(result.sync_result)
      setDialogOpen(false)
      setGithubRepo('')
      setGithubToken('')
      setFigmaFileKey('')
      setFigmaToken('')
      setTrelloBoardId('')
      setTrelloToken('')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSyncAll = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const results = await syncAllConnectors(roomId)
      setSyncResult(results)
      load()
    } catch (err) {
      setSyncResult({ error: err.message })
    } finally {
      setSyncing(false)
    }
  }

  const handleSync = async (connectorId) => {
    setSyncing(true)
    try {
      const result = await syncConnector(roomId, connectorId)
      setSyncResult(result.sync_result)
      load()
    } catch (err) {
      setSyncResult({ error: err.message })
    } finally {
      setSyncing(false)
    }
  }

  const handleRemoveConnector = async (connectorId) => {
    if (!confirm('Remove this connector? Entities already synced will remain in the graph.')) return
    try {
      await removeConnector(roomId, connectorId)
      load()
    } catch (err) {
      alert('Failed to remove: ' + err.message)
    }
  }

  const filteredEntities = filterSource === 'all'
    ? entities
    : entities.filter(e => e.source === filterSource)

  const sources = [...new Set(entities.map(e => e.source).filter(Boolean))]

  const formatSyncResult = (result) => {
    if (result.error) return result.error
    if (result.stats) {
      const s = result.stats
      return `Synced: ${s.cards || 0} cards, ${s.checklist_items || 0} checklist items, ${s.members || 0} members, ${s.labels || 0} labels, ${s.comments || 0} comments, ${s.attachments || 0} attachments`
    }
    return `Synced: ${result.branches || 0} branches, ${result.pull_requests || 0} PRs, ${result.issues || 0} issues, ${result.commits || 0} commits, ${result.files || 0} files, ${result.pages || 0} pages, ${result.frames || 0} frames`
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.85rem', fontWeight: 600 }}>
          Connectors & Entities
        </Typography>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {connectors.length > 0 && (
            <Tooltip title="Sync all connectors">
              <IconButton size="small" onClick={handleSyncAll} disabled={syncing} sx={{ color: 'primary.main' }}>
                <SyncIcon fontSize="small" sx={{ animation: syncing ? 'spin 1s linear infinite' : 'none', '@keyframes spin': { from: { transform: 'rotate(0deg)' }, to: { transform: 'rotate(360deg)' } } }} />
              </IconButton>
            </Tooltip>
          )}
          <Tooltip title="Add connector">
            <IconButton size="small" onClick={() => setDialogOpen(true)} sx={{ color: 'primary.main' }}>
              <AddIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Active connectors */}
      {connectors.length > 0 && (
        <Box sx={{ px: 2, py: 1, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <Typography sx={{ fontSize: '0.6rem', textTransform: 'uppercase', color: 'text.secondary', mb: 0.5, letterSpacing: '0.1em' }}>
            Connected
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {connectors.map(c => (
              <Chip
                key={c.connector_id}
                icon={CONNECTOR_ICONS[c.connector_type] || <LinkIcon sx={{ fontSize: '0.8rem' }} />}
                label={c.connector_type}
                size="small"
                onClick={() => handleSync(c.connector_id)}
                onDelete={() => handleRemoveConnector(c.connector_id)}
                sx={{
                  fontSize: '0.65rem', height: 22,
                  bgcolor: SOURCE_COLORS[c.connector_type] || 'rgba(255,255,255,0.05)',
                  color: '#fff',
                  cursor: 'pointer',
                  '& .MuiChip-deleteIcon': {
                    fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)',
                    '&:hover': { color: '#ff6b6b' },
                  },
                }}
              />
            ))}
          </Box>
        </Box>
      )}

      {/* Sync result alert */}
      {syncResult && (
        <Box sx={{ px: 2, pt: 1 }}>
          <Alert
            severity={syncResult.error ? 'error' : 'success'}
            onClose={() => setSyncResult(null)}
            sx={{ fontSize: '0.7rem', py: 0 }}
          >
            {formatSyncResult(syncResult)}
          </Alert>
        </Box>
      )}

      {/* Filter */}
      {sources.length > 1 && (
        <Box sx={{ px: 2, py: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          <Chip label="All" size="small" clickable
            variant={filterSource === 'all' ? 'filled' : 'outlined'}
            onClick={() => setFilterSource('all')}
            sx={{ fontSize: '0.6rem', height: 20 }}
          />
          {sources.map(s => (
            <Chip key={s} label={s} size="small" clickable
              variant={filterSource === s ? 'filled' : 'outlined'}
              onClick={() => setFilterSource(s)}
              sx={{
                fontSize: '0.6rem', height: 20,
                bgcolor: filterSource === s ? (SOURCE_COLORS[s] || 'rgba(255,255,255,0.1)') : 'transparent',
              }}
            />
          ))}
        </Box>
      )}

      {/* Entity list */}
      <Box sx={{ flex: 1, overflow: 'auto', px: 2, py: 1 }}>
        {filteredEntities.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
            <LinkIcon sx={{ fontSize: '2rem', mb: 1, opacity: 0.3 }} />
            <Typography sx={{ fontSize: '0.8rem' }}>
              {connectors.length === 0
                ? 'Connect GitHub, Figma, or Trello to pull entities into the graph.'
                : 'No entities synced yet. Try syncing your connectors.'
              }
            </Typography>
          </Box>
        )}

        {filteredEntities.map(entity => (
          <EntityCard key={entity.id} entity={entity} />
        ))}
      </Box>

      {/* Stats */}
      <Box sx={{ px: 2, py: 1, borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between' }}>
        <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
          {entities.length} entities in graph
        </Typography>
        <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
          {connectors.length} connector{connectors.length !== 1 ? 's' : ''}
        </Typography>
      </Box>

      {/* Add Connector Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontFamily: '"JetBrains Mono"', fontSize: '1rem' }}>
          Connect Integration
        </DialogTitle>
        <DialogContent>
          {error && <Alert severity="error" sx={{ mb: 2, fontSize: '0.8rem' }}>{error}</Alert>}

          <FormControl fullWidth size="small" sx={{ mt: 1, mb: 2 }}>
            <InputLabel>Platform</InputLabel>
            <Select value={connectorType} onChange={(e) => setConnectorType(e.target.value)} label="Platform">
              <MenuItem value="github">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <GitHubIcon sx={{ fontSize: '1rem' }} /> GitHub
                </Box>
              </MenuItem>
              <MenuItem value="figma">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <BrushIcon sx={{ fontSize: '1rem' }} /> Figma
                </Box>
              </MenuItem>
              <MenuItem value="trello">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ViewKanbanIcon sx={{ fontSize: '1rem' }} /> Trello
                </Box>
              </MenuItem>
            </Select>
          </FormControl>

          {connectorType === 'github' && (
            <>
              <TextField
                fullWidth size="small" label="Repository" placeholder="owner/repo"
                value={githubRepo} onChange={(e) => setGithubRepo(e.target.value)}
                helperText="e.g., darwinai/darwin-evolve-beta"
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth size="small" label="Personal Access Token" type="password"
                placeholder="ghp_..."
                value={githubToken} onChange={(e) => setGithubToken(e.target.value)}
                helperText="github.com → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)"
              />
            </>
          )}

          {connectorType === 'figma' && (
            <>
              <TextField
                fullWidth size="small" label="File Key"
                placeholder="abc123def456"
                value={figmaFileKey} onChange={(e) => setFigmaFileKey(e.target.value)}
                helperText="From the Figma URL: figma.com/file/[FILE_KEY]/..."
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth size="small" label="Personal Access Token" type="password"
                placeholder="figd_..."
                value={figmaToken} onChange={(e) => setFigmaToken(e.target.value)}
                helperText="figma.com → Settings → Personal Access Tokens"
              />
            </>
          )}

          {connectorType === 'trello' && (
            <>
              <TextField
                fullWidth size="small" label="Board ID"
                placeholder="xaezXoD8"
                value={trelloBoardId} onChange={(e) => setTrelloBoardId(e.target.value)}
                helperText="From the Trello URL: trello.com/b/[BOARD_ID]/..."
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth size="small" label="API Token" type="password"
                placeholder="ATTA..."
                value={trelloToken} onChange={(e) => setTrelloToken(e.target.value)}
                helperText="trello.com/app-key → authorize to get token"
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} sx={{ color: 'text.secondary' }}>Cancel</Button>
          <Button
            onClick={handleAddConnector} variant="contained" disabled={loading}
            sx={{ bgcolor: 'primary.main', color: '#0a0e17' }}
          >
            {loading ? <CircularProgress size={18} /> : 'Connect & Sync'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}


function EntityCard({ entity }) {
  const icon = ENTITY_ICONS[entity.type] || <LinkIcon sx={{ fontSize: '0.9rem' }} />
  const sourceColor = SOURCE_COLORS[entity.source] || 'rgba(255,255,255,0.1)'

  return (
    <Paper sx={{
      px: 1.5, py: 1, mb: 0.5, bgcolor: 'rgba(255,255,255,0.02)',
      border: '1px solid rgba(255,255,255,0.04)',
      borderLeft: `3px solid ${sourceColor}`,
      borderRadius: 1,
      '&:hover': { bgcolor: 'rgba(255,255,255,0.04)' },
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        {icon}
        <Typography sx={{ fontSize: '0.75rem', fontWeight: 500, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {entity.name}
        </Typography>
        <Chip label={entity.type} size="small"
          sx={{ fontSize: '0.5rem', height: 16, bgcolor: 'rgba(255,255,255,0.05)' }}
        />
      </Box>
      {entity.relationships && entity.relationships.length > 0 && (
        <Box sx={{ mt: 0.5, pl: 2 }}>
          {entity.relationships.slice(0, 3).map((rel, i) => (
            <Typography key={i} sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
              → {rel.rel_type} → {rel.target_name}
            </Typography>
          ))}
        </Box>
      )}
    </Paper>
  )
}