import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Button, Chip, IconButton, Dialog, DialogTitle,
  DialogContent, DialogActions, Select, MenuItem, FormControl, InputLabel,
  CircularProgress, Paper, Tooltip, TextField, Alert, Tabs, Tab,
} from '@mui/material'
import DescriptionIcon from '@mui/icons-material/Description'
import GavelIcon from '@mui/icons-material/Gavel'
import GridOnIcon from '@mui/icons-material/GridOn'
import CompareArrowsIcon from '@mui/icons-material/CompareArrows'
import NewReleasesIcon from '@mui/icons-material/NewReleases'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import HistoryIcon from '@mui/icons-material/History'
import CloseIcon from '@mui/icons-material/Close'
import {
  generateArtifact, listArtifacts, getArtifact,
} from '../api/client'

const ARTIFACT_TYPES = [
  { key: 'PRD', label: 'PRD', icon: <DescriptionIcon sx={{ fontSize: '1rem' }} />, description: 'Product Requirements Document from graph context' },
  { key: 'DecisionLog', label: 'Decisions', icon: <GavelIcon sx={{ fontSize: '1rem' }} />, description: 'Extract all decisions made in chat' },
  { key: 'TraceabilityMatrix', label: 'Traceability', icon: <GridOnIcon sx={{ fontSize: '1rem' }} />, description: 'Requirement → Design → Code → Test matrix' },
  { key: 'DriftDetection', label: 'Drift Report', icon: <CompareArrowsIcon sx={{ fontSize: '1rem' }} />, description: 'Find gaps between designs, code, and decisions' },
  { key: 'ReleaseNotes', label: 'Release Notes', icon: <NewReleasesIcon sx={{ fontSize: '1rem' }} />, description: 'Generate release notes from PRs and discussion' },
]

const TYPE_COLORS = {
  PRD: '#6ee7b7',
  DecisionLog: '#fbbf24',
  TraceabilityMatrix: '#818cf8',
  DriftDetection: '#f87171',
  ReleaseNotes: '#38bdf8',
}

export default function ArtifactsPanel({ roomId }) {
  const [artifacts, setArtifacts] = useState([])
  const [generating, setGenerating] = useState(false)
  const [selectedType, setSelectedType] = useState('PRD')
  const [instructions, setInstructions] = useState('')
  const [viewingArtifact, setViewingArtifact] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState(0)

  const load = () => listArtifacts(roomId).then(setArtifacts).catch(console.error)

  useEffect(() => { load() }, [roomId])

  const handleGenerate = async () => {
    setError('')
    setGenerating(true)
    try {
      const result = await generateArtifact(roomId, selectedType, instructions)
      setViewingArtifact(result)
      setInstructions('')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  const handleViewArtifact = async (artifactId) => {
    try {
      const result = await getArtifact(roomId, artifactId)
      setViewingArtifact(result)
    } catch (err) {
      alert('Failed to load: ' + err.message)
    }
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.85rem', fontWeight: 600 }}>
          Artifacts
        </Typography>
      </Box>

      {/* Tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth"
        sx={{ borderBottom: '1px solid rgba(255,255,255,0.06)', minHeight: 36,
          '& .MuiTab-root': { minHeight: 36, fontSize: '0.7rem', textTransform: 'none' } }}>
        <Tab label="Generate" />
        <Tab label={`History (${artifacts.length})`} />
      </Tabs>

      {/* Generate Tab */}
      {tab === 0 && (
        <Box sx={{ flex: 1, overflow: 'auto', px: 2, py: 1.5 }}>
          {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 1.5, fontSize: '0.75rem', py: 0 }}>{error}</Alert>}

          <Typography sx={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'text.secondary', mb: 1, letterSpacing: '0.1em' }}>
            Choose artifact type
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 2 }}>
            {ARTIFACT_TYPES.map(t => (
              <Paper key={t.key}
                onClick={() => setSelectedType(t.key)}
                sx={{
                  px: 1.5, py: 1, cursor: 'pointer',
                  bgcolor: selectedType === t.key ? 'rgba(110, 231, 183, 0.08)' : 'rgba(255,255,255,0.02)',
                  border: selectedType === t.key ? `1px solid ${TYPE_COLORS[t.key]}40` : '1px solid rgba(255,255,255,0.04)',
                  borderLeft: `3px solid ${TYPE_COLORS[t.key]}`,
                  borderRadius: 1,
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.04)' },
                }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  {t.icon}
                  <Typography sx={{ fontSize: '0.8rem', fontWeight: 600 }}>{t.label}</Typography>
                </Box>
                <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary', mt: 0.3 }}>
                  {t.description}
                </Typography>
              </Paper>
            ))}
          </Box>

          <TextField
            fullWidth size="small" multiline rows={2}
            placeholder="Additional instructions (optional)..."
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            sx={{ mb: 1.5, '& .MuiOutlinedInput-root': { fontSize: '0.8rem' } }}
          />

          <Button
            fullWidth variant="contained" disabled={generating}
            onClick={handleGenerate}
            startIcon={generating ? <CircularProgress size={16} /> : <AutoAwesomeIcon sx={{ fontSize: '1rem' }} />}
            sx={{
              bgcolor: TYPE_COLORS[selectedType], color: '#0a0e17',
              fontWeight: 600, py: 1,
              '&:hover': { bgcolor: TYPE_COLORS[selectedType], filter: 'brightness(1.15)' },
              '&.Mui-disabled': { bgcolor: `${TYPE_COLORS[selectedType]}30` },
            }}
          >
            {generating ? 'Generating...' : `Generate ${ARTIFACT_TYPES.find(t => t.key === selectedType)?.label}`}
          </Button>
        </Box>
      )}

      {/* History Tab */}
      {tab === 1 && (
        <Box sx={{ flex: 1, overflow: 'auto', px: 2, py: 1 }}>
          {artifacts.length === 0 && (
            <Box sx={{ textAlign: 'center', py: 4, color: 'text.secondary' }}>
              <DescriptionIcon sx={{ fontSize: '2rem', mb: 1, opacity: 0.3 }} />
              <Typography sx={{ fontSize: '0.8rem' }}>
                No artifacts generated yet.
              </Typography>
            </Box>
          )}

          {artifacts.map(art => (
            <Paper key={art.artifact_id}
              onClick={() => handleViewArtifact(art.artifact_id)}
              sx={{
                px: 1.5, py: 1, mb: 0.5, cursor: 'pointer',
                bgcolor: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.04)',
                borderLeft: `3px solid ${TYPE_COLORS[art.type] || '#666'}`,
                borderRadius: 1,
                '&:hover': { bgcolor: 'rgba(255,255,255,0.04)' },
              }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  {ARTIFACT_TYPES.find(t => t.key === art.type)?.icon || <DescriptionIcon sx={{ fontSize: '0.9rem' }} />}
                  <Typography sx={{ fontSize: '0.75rem', fontWeight: 600 }}>{art.type}</Typography>
                  <Chip label={`v${art.version}`} size="small"
                    sx={{ fontSize: '0.5rem', height: 16, bgcolor: `${TYPE_COLORS[art.type] || '#666'}20`, color: TYPE_COLORS[art.type] || '#ccc' }} />
                </Box>
              </Box>
              <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary', mt: 0.3 }}>
                {art.generated_by} · {art.created_at ? new Date(art.created_at).toLocaleDateString() : ''}
              </Typography>
            </Paper>
          ))}
        </Box>
      )}

      {/* Artifact Viewer Dialog */}
      <Dialog open={!!viewingArtifact} onClose={() => setViewingArtifact(null)} maxWidth="md" fullWidth
        PaperProps={{ sx: { bgcolor: 'background.paper', maxHeight: '80vh' } }}>
        {viewingArtifact && (
          <>
            <DialogTitle sx={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {ARTIFACT_TYPES.find(t => t.key === viewingArtifact.type)?.icon}
                <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '1rem' }}>
                  {viewingArtifact.type}
                </Typography>
                {viewingArtifact.version && (
                  <Chip label={`v${viewingArtifact.version}`} size="small"
                    sx={{ fontSize: '0.6rem', height: 20, bgcolor: `${TYPE_COLORS[viewingArtifact.type] || '#666'}20` }} />
                )}
              </Box>
              <IconButton size="small" onClick={() => setViewingArtifact(null)}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </DialogTitle>
            <DialogContent sx={{ py: 2 }}>
              <Paper sx={{
                p: 3, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: 2, maxHeight: '60vh', overflow: 'auto',
              }}>
                <Typography sx={{
                  fontSize: '0.85rem', lineHeight: 1.8, whiteSpace: 'pre-wrap',
                  fontFamily: '"DM Sans", sans-serif',
                }}>
                  {viewingArtifact.content}
                </Typography>
              </Paper>
              <Box sx={{ display: 'flex', gap: 1, mt: 1.5, justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
                  Model: {viewingArtifact.model} · Cost: ${Number(viewingArtifact.cost || 0).toFixed(4)}
                </Typography>
                {viewingArtifact.referenced_entities && viewingArtifact.referenced_entities.length > 0 && (
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {viewingArtifact.referenced_entities.slice(0, 5).map(e => (
                      <Chip key={e} label={e} size="small"
                        sx={{ fontSize: '0.5rem', height: 16, bgcolor: 'rgba(110, 231, 183, 0.08)', color: 'primary.main' }} />
                    ))}
                  </Box>
                )}
              </Box>
            </DialogContent>
          </>
        )}
      </Dialog>
    </Box>
  )
}
