import React, { useState, useEffect, useRef } from 'react'
import {
  Box, Typography, LinearProgress, Button, Chip, Collapse, IconButton,
  CircularProgress,
} from '@mui/material'
import PsychologyIcon from '@mui/icons-material/Psychology'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import LockIcon from '@mui/icons-material/Lock'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import AutorenewIcon from '@mui/icons-material/Autorenew'
import { getTrainingReadiness, startTraining, getTrainingStatus } from '../api/client'

const TYPE_ICONS = {
  File: '📄',
  Repository: '📦',
  Branch: '🌿',
  PullRequest: '🔀',
  Issue: '🐛',
  Commit: '💾',
  FigmaFile: '🎨',
  FigmaPage: '📐',
  FigmaFrame: '🖼',
  FigmaComponent: '🧩',
  Component: '⚙️',
  Requirement: '📋',
}

export default function TrainingPanel() {
  const [data, setData] = useState(null)
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [trainingJobId, setTrainingJobId] = useState(null)
  const [trainingStatus, setTrainingStatus] = useState(null)
  const pollRef = useRef(null)

  const load = async () => {
    setLoading(true)
    try {
      const result = await getTrainingReadiness()
      setData(result)
      // If there's an active job, start polling
      if (result.active_job && !['complete', 'error'].includes(result.active_job.status)) {
        setTrainingJobId(result.active_job.job_id)
        setTrainingStatus(result.active_job)
      }
    } catch (err) {
      console.error('Training readiness error:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // Poll training status
  useEffect(() => {
    if (!trainingJobId) return

    const poll = async () => {
      try {
        const status = await getTrainingStatus(trainingJobId)
        setTrainingStatus(status)
        if (['complete', 'error'].includes(status.status)) {
          clearInterval(pollRef.current)
          pollRef.current = null
          load() // Refresh readiness data
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }

    pollRef.current = setInterval(poll, 5000)
    poll() // Immediate first poll

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [trainingJobId])

  const handleStartTraining = async () => {
    try {
      const result = await startTraining()
      setTrainingJobId(result.job_id)
      setTrainingStatus({ status: 'queued', progress: 0, message: 'Training job queued' })
      setExpanded(true)
    } catch (err) {
      alert(`Training failed to start: ${err.message}`)
    }
  }

  if (!data) return null

  const { ready, current, progress, estimated_weeks_to_ready, thresholds, existing_model } = data
  const relPct = progress.relationships_pct
  const crossPct = progress.cross_type_pct
  const overallPct = Math.round((relPct + crossPct) / 2)

  const isTraining = trainingStatus && !['complete', 'error'].includes(trainingStatus.status)
  const trainingComplete = trainingStatus?.status === 'complete'
  const trainingError = trainingStatus?.status === 'error'

  return (
    <Box sx={{
      mx: 1.5, my: 1, p: 1.5, borderRadius: 2,
      bgcolor: (ready || existing_model) ? 'rgba(110, 231, 183, 0.06)' : 'rgba(255, 255, 255, 0.02)',
      border: `1px solid ${(ready || existing_model) ? 'rgba(110, 231, 183, 0.2)' : 'rgba(255,255,255,0.06)'}`,
    }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PsychologyIcon sx={{ fontSize: '1rem', color: (ready || existing_model) ? '#6ee7b7' : '#6b7280' }} />
          <Typography sx={{
            fontFamily: '"JetBrains Mono"', fontSize: '0.7rem', fontWeight: 600,
            color: (ready || existing_model) ? '#6ee7b7' : 'text.secondary',
          }}>
            Custom Model
          </Typography>
          {existing_model && (
            <Chip label="TRAINED" size="small" sx={{
              fontSize: '0.45rem', height: 14, bgcolor: 'rgba(110, 231, 183, 0.15)',
              color: '#6ee7b7', fontWeight: 700,
            }} />
          )}
        </Box>
        <IconButton size="small" onClick={() => setExpanded(!expanded)} sx={{ color: 'text.secondary', p: 0.25 }}>
          {expanded ? <ExpandLessIcon sx={{ fontSize: '0.9rem' }} /> : <ExpandMoreIcon sx={{ fontSize: '0.9rem' }} />}
        </IconButton>
      </Box>

      {/* Progress bar — graph density */}
      {!existing_model && (
        <Box sx={{ mt: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
              {current.total_relationships} / {thresholds.min_relationships} relationships
            </Typography>
            <Typography sx={{ fontSize: '0.6rem', color: ready ? '#6ee7b7' : 'text.secondary', fontWeight: 600 }}>
              {overallPct}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={overallPct}
            sx={{
              height: 4, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.06)',
              '& .MuiLinearProgress-bar': {
                borderRadius: 2,
                background: ready
                  ? 'linear-gradient(90deg, #6ee7b7, #34d399)'
                  : 'linear-gradient(90deg, #4b5563, #6b7280)',
              },
            }}
          />
        </Box>
      )}

      {/* Training progress bar */}
      {isTraining && (
        <Box sx={{ mt: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography sx={{ fontSize: '0.55rem', color: '#fbbf24' }}>
              {trainingStatus.status === 'queued' ? '⏳ Queued' :
               trainingStatus.status === 'generating_data' ? '📊 Generating data' :
               trainingStatus.status === 'initializing' ? '🔧 Initializing Tinker' :
               trainingStatus.status === 'training' ? '🧠 Training' :
               trainingStatus.status === 'saving' ? '💾 Saving weights' : trainingStatus.status}
            </Typography>
            <Typography sx={{ fontSize: '0.55rem', color: '#fbbf24', fontWeight: 600 }}>
              {trainingStatus.progress}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={trainingStatus.progress}
            sx={{
              height: 4, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.06)',
              '& .MuiLinearProgress-bar': {
                borderRadius: 2,
                background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
              },
            }}
          />
          <Typography sx={{ fontSize: '0.5rem', color: 'text.secondary', mt: 0.5, fontStyle: 'italic' }}>
            {trainingStatus.message}
          </Typography>
        </Box>
      )}

      {/* Training complete */}
      {trainingComplete && !existing_model && (
        <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <CheckCircleIcon sx={{ fontSize: '0.8rem', color: '#6ee7b7' }} />
          <Typography sx={{ fontSize: '0.55rem', color: '#6ee7b7' }}>
            Training complete! Reload to use custom model.
          </Typography>
        </Box>
      )}

      {/* Training error */}
      {trainingError && (
        <Box sx={{ mt: 1 }}>
          <Typography sx={{ fontSize: '0.55rem', color: '#f87171' }}>
            ❌ {trainingStatus.message}
          </Typography>
        </Box>
      )}

      {/* Expanded details */}
      <Collapse in={expanded}>
        <Box sx={{ mt: 1.5 }}>
          {/* Existing model info */}
          {existing_model && (
            <Box sx={{ mb: 1, p: 1, borderRadius: 1, bgcolor: 'rgba(110, 231, 183, 0.04)' }}>
              <Typography sx={{ fontSize: '0.55rem', color: '#6ee7b7', fontWeight: 600, mb: 0.3 }}>
                Active Model
              </Typography>
              <Typography sx={{ fontSize: '0.5rem', color: 'text.secondary' }}>
                ID: {existing_model.model_id}
              </Typography>
              <Typography sx={{ fontSize: '0.5rem', color: 'text.secondary' }}>
                Trained on {existing_model.training_examples} examples · Loss: {existing_model.final_loss?.toFixed(4)}
              </Typography>
              <Typography sx={{ fontSize: '0.5rem', color: 'text.secondary' }}>
                Created: {new Date(existing_model.created_at).toLocaleDateString()}
              </Typography>
            </Box>
          )}

          {/* Cross-type progress */}
          {!existing_model && (
            <Box sx={{ mb: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.3 }}>
                <Typography sx={{ fontSize: '0.55rem', color: 'text.secondary' }}>
                  Cross-type edges
                </Typography>
                <Typography sx={{ fontSize: '0.55rem', color: 'text.secondary' }}>
                  {current.cross_type_relationships} / {thresholds.min_cross_type_relationships}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={crossPct}
                sx={{
                  height: 3, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.04)',
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 2, bgcolor: crossPct >= 100 ? '#6ee7b7' : '#4b5563',
                  },
                }}
              />
            </Box>
          )}

          {/* Entity breakdown */}
          <Typography sx={{ fontSize: '0.55rem', color: 'text.secondary', mb: 0.5, fontWeight: 600 }}>
            Entity Breakdown
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {Object.entries(current.node_counts_by_type || {}).map(([type, count]) => (
              <Chip
                key={type}
                label={`${TYPE_ICONS[type] || '●'} ${type}: ${count}`}
                size="small"
                sx={{
                  fontSize: '0.5rem', height: 18,
                  bgcolor: 'rgba(255,255,255,0.04)',
                  color: 'text.secondary',
                }}
              />
            ))}
          </Box>

          {!ready && !existing_model && estimated_weeks_to_ready > 0 && (
            <Typography sx={{ fontSize: '0.55rem', color: 'text.secondary', mt: 1, fontStyle: 'italic' }}>
              ~{estimated_weeks_to_ready} weeks to unlock at current pace
            </Typography>
          )}
        </Box>
      </Collapse>

      {/* Action button */}
      <Box sx={{ mt: 1 }}>
        {isTraining ? (
          <Button
            fullWidth size="small" disabled
            startIcon={<AutorenewIcon sx={{ fontSize: '0.8rem', animation: 'spin 1s linear infinite', '@keyframes spin': { '0%': { transform: 'rotate(0deg)' }, '100%': { transform: 'rotate(360deg)' } } }} />}
            sx={{
              py: 0.5, fontSize: '0.6rem', borderRadius: 1.5,
              fontFamily: '"JetBrains Mono"', textTransform: 'none',
              color: '#fbbf24',
            }}
          >
            Training in progress...
          </Button>
        ) : existing_model ? (
          <Button
            fullWidth size="small"
            startIcon={<RocketLaunchIcon sx={{ fontSize: '0.8rem' }} />}
            onClick={handleStartTraining}
            sx={{
              py: 0.5, fontSize: '0.6rem', borderRadius: 1.5,
              fontFamily: '"JetBrains Mono"', fontWeight: 600, textTransform: 'none',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: 'text.secondary',
              '&:hover': { background: 'rgba(255,255,255,0.08)' },
            }}
          >
            Retrain Model
          </Button>
        ) : ready ? (
          <Button
            fullWidth size="small"
            startIcon={<CheckCircleIcon sx={{ fontSize: '0.8rem' }} />}
            onClick={handleStartTraining}
            sx={{
              py: 0.5, fontSize: '0.65rem', borderRadius: 1.5,
              fontFamily: '"JetBrains Mono"', fontWeight: 600, textTransform: 'none',
              background: 'linear-gradient(135deg, rgba(110, 231, 183, 0.15) 0%, rgba(52, 211, 153, 0.15) 100%)',
              border: '1px solid rgba(110, 231, 183, 0.3)',
              color: '#6ee7b7',
              '&:hover': {
                background: 'linear-gradient(135deg, rgba(110, 231, 183, 0.25) 0%, rgba(52, 211, 153, 0.25) 100%)',
              },
            }}
          >
            Train Custom Model
          </Button>
        ) : (
          <Button
            fullWidth size="small" disabled
            startIcon={<LockIcon sx={{ fontSize: '0.7rem' }} />}
            sx={{
              py: 0.5, fontSize: '0.6rem', borderRadius: 1.5,
              fontFamily: '"JetBrains Mono"', textTransform: 'none',
              color: '#4b5563',
            }}
          >
            Train Model (locked)
          </Button>
        )}
      </Box>
    </Box>
  )
}
