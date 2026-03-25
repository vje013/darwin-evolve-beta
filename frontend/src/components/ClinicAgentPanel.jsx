import React, { useState, useRef } from 'react'
import {
  Box, Typography, Button, TextField, LinearProgress, Chip,
  IconButton, Paper, Select, MenuItem, FormControl, InputLabel,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import GroupsIcon from '@mui/icons-material/Groups'
import WarningIcon from '@mui/icons-material/Warning'
import { analyzeClinicFeature } from '../api/client'

export default function ClinicAgentPanel({ onBack }) {
  const [image, setImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const [featureFocus, setFeatureFocus] = useState('')
  const [specificQuestion, setSpecificQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState(null)
  const [selectedPersona, setSelectedPersona] = useState('')
  const fileRef = useRef()

  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setImage(file)
      const reader = new FileReader()
      reader.onload = (ev) => setImagePreview(ev.target.result)
      reader.readAsDataURL(file)
    }
  }

  const handleAnalyze = async () => {
    if (!image || !featureFocus || !specificQuestion) return
    setLoading(true)
    setProgress(0)
    setResults(null)

    const interval = setInterval(() => {
      setProgress(prev => Math.min(prev + 2, 95))
    }, 1500)

    try {
      const data = await analyzeClinicFeature(image, featureFocus, specificQuestion)
      setResults(data)
      setProgress(100)
    } catch (err) {
      alert(`Analysis failed: ${err.message}`)
    } finally {
      clearInterval(interval)
      setLoading(false)
    }
  }

  const selectedResult = selectedPersona && results?.results?.[selectedPersona]

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{
        px: 3, py: 2, borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 1.5,
      }}>
        <IconButton size="small" onClick={onBack} sx={{ color: 'text.secondary' }}>
          <ArrowBackIcon fontSize="small" />
        </IconButton>
        <GroupsIcon sx={{ color: '#818cf8' }} />
        <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '1rem', fontWeight: 700, color: '#818cf8' }}>
          Customer Clinic Agent
        </Typography>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', p: 3 }}>
        {/* Input Section */}
        <Box sx={{ display: 'flex', gap: 3, mb: 3, flexWrap: 'wrap' }}>
          {/* Image Upload */}
          <Paper
            onClick={() => fileRef.current?.click()}
            sx={{
              width: 220, height: 180, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexDirection: 'column', gap: 1,
              bgcolor: 'rgba(129, 140, 248, 0.04)',
              border: '2px dashed rgba(129, 140, 248, 0.2)',
              borderRadius: 3,
              overflow: 'hidden',
              '&:hover': { border: '2px dashed rgba(129, 140, 248, 0.5)' },
            }}
          >
            {imagePreview ? (
              <img src={imagePreview} alt="CID" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <>
                <CloudUploadIcon sx={{ fontSize: '2rem', color: '#818cf8', opacity: 0.5 }} />
                <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', textAlign: 'center', px: 2 }}>
                  Upload CID Image
                </Typography>
              </>
            )}
            <input ref={fileRef} type="file" accept="image/*" hidden onChange={handleImageSelect} />
          </Paper>

          {/* Text Inputs */}
          <Box sx={{ flex: 1, minWidth: 250, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth size="small" label="Feature to Analyze"
              placeholder="e.g., radio controls, climate interface"
              value={featureFocus} onChange={e => setFeatureFocus(e.target.value)}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
            <TextField
              fullWidth size="small" label="Specific Question"
              placeholder="e.g., button size, placement, menu depth"
              value={specificQuestion} onChange={e => setSpecificQuestion(e.target.value)}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
            <Button
              variant="contained"
              onClick={handleAnalyze}
              disabled={loading || !image || !featureFocus || !specificQuestion}
              startIcon={<GroupsIcon />}
              sx={{
                borderRadius: 2, py: 1.2,
                bgcolor: '#818cf8', color: '#0a0e17',
                fontFamily: '"JetBrains Mono"', fontWeight: 700,
                fontSize: '0.8rem', textTransform: 'none',
                '&:hover': { bgcolor: '#a5b4fc' },
              }}
            >
              {loading ? 'Analyzing 20 Personas...' : 'Run Customer Clinic'}
            </Button>
          </Box>
        </Box>

        {/* Progress */}
        {loading && (
          <Box sx={{ mb: 3 }}>
            <LinearProgress variant="determinate" value={progress} sx={{
              height: 6, borderRadius: 3, bgcolor: 'rgba(129,140,248,0.1)',
              '& .MuiLinearProgress-bar': { borderRadius: 3, bgcolor: '#818cf8' },
            }} />
            <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary', mt: 0.5 }}>
              Analyzing across 20 customer personas... {Math.round(progress)}%
            </Typography>
          </Box>
        )}

        {/* Results */}
        {results && (
          <>
            {/* Summary Stats */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
              <Paper sx={{ px: 3, py: 2, borderRadius: 3, bgcolor: 'rgba(129,140,248,0.06)', border: '1px solid rgba(129,140,248,0.15)', flex: 1, minWidth: 140 }}>
                <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Avg Satisfaction
                </Typography>
                <Typography sx={{
                  fontFamily: '"JetBrains Mono"', fontSize: '1.8rem', fontWeight: 700,
                  color: results.avg_satisfaction >= 7 ? '#6ee7b7' : results.avg_satisfaction >= 5 ? '#fbbf24' : '#f87171',
                }}>
                  {results.avg_satisfaction}/10
                </Typography>
              </Paper>
              <Paper sx={{ px: 3, py: 2, borderRadius: 3, bgcolor: 'rgba(129,140,248,0.06)', border: '1px solid rgba(129,140,248,0.15)', flex: 1, minWidth: 140 }}>
                <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Personas Analyzed
                </Typography>
                <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '1.8rem', fontWeight: 700, color: '#818cf8' }}>
                  {results.persona_count}
                </Typography>
              </Paper>
              <Paper sx={{ px: 3, py: 2, borderRadius: 3, bgcolor: results.deal_breaker_count > 0 ? 'rgba(248,113,113,0.06)' : 'rgba(129,140,248,0.06)', border: `1px solid ${results.deal_breaker_count > 0 ? 'rgba(248,113,113,0.15)' : 'rgba(129,140,248,0.15)'}`, flex: 1, minWidth: 140 }}>
                <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Deal Breakers
                </Typography>
                <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '1.8rem', fontWeight: 700, color: results.deal_breaker_count > 0 ? '#f87171' : '#6ee7b7' }}>
                  {results.deal_breaker_count}
                </Typography>
              </Paper>
            </Box>

            {/* Score Rankings */}
            <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.8rem', fontWeight: 600, mb: 1.5 }}>
              Satisfaction Rankings
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 3 }}>
              {Object.entries(results.results)
                .sort((a, b) => (b[1].satisfaction_score || 0) - (a[1].satisfaction_score || 0))
                .map(([name, r]) => (
                  <Box
                    key={name}
                    onClick={() => setSelectedPersona(name)}
                    sx={{
                      display: 'flex', alignItems: 'center', gap: 1.5, px: 2, py: 1,
                      borderRadius: 2, cursor: 'pointer',
                      bgcolor: selectedPersona === name ? 'rgba(129,140,248,0.1)' : 'transparent',
                      border: selectedPersona === name ? '1px solid rgba(129,140,248,0.3)' : '1px solid transparent',
                      '&:hover': { bgcolor: 'rgba(129,140,248,0.06)' },
                    }}
                  >
                    <Box sx={{
                      width: 32, height: 32, borderRadius: 2, display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontFamily: '"JetBrains Mono"', fontSize: '0.75rem', fontWeight: 700,
                      bgcolor: (r.satisfaction_score || 0) >= 7 ? 'rgba(110,231,183,0.15)' : (r.satisfaction_score || 0) >= 5 ? 'rgba(251,191,36,0.15)' : 'rgba(248,113,113,0.15)',
                      color: (r.satisfaction_score || 0) >= 7 ? '#6ee7b7' : (r.satisfaction_score || 0) >= 5 ? '#fbbf24' : '#f87171',
                    }}>
                      {r.satisfaction_score || 0}
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <Typography sx={{ fontSize: '0.75rem', fontWeight: 500 }}>{name}</Typography>
                      <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
                        Age {r.persona?.age} · Tech {r.persona?.tech_comfort}/10 · {r.persona?.primary_use}
                      </Typography>
                    </Box>
                    {r.deal_breaker && <WarningIcon sx={{ fontSize: '0.9rem', color: '#f87171' }} />}
                  </Box>
                ))}
            </Box>

            {/* Selected Persona Detail */}
            {selectedResult && (
              <Paper sx={{ p: 3, borderRadius: 3, bgcolor: 'rgba(129,140,248,0.04)', border: '1px solid rgba(129,140,248,0.15)' }}>
                <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.85rem', fontWeight: 700, color: '#818cf8', mb: 1 }}>
                  {selectedPersona}
                </Typography>
                <Typography sx={{ fontSize: '0.75rem', color: 'text.secondary', fontStyle: 'italic', mb: 2 }}>
                  "{selectedResult.customer_quote}"
                </Typography>

                <Typography sx={{ fontSize: '0.7rem', fontWeight: 600, mb: 0.5 }}>Analysis</Typography>
                <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', mb: 1.5 }}>
                  {selectedResult.feature_analysis}
                </Typography>

                <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                  <Box sx={{ flex: 1, minWidth: 180 }}>
                    <Typography sx={{ fontSize: '0.65rem', fontWeight: 600, color: '#6ee7b7', mb: 0.5 }}>Likes</Typography>
                    {(Array.isArray(selectedResult.likes) ? selectedResult.likes : [selectedResult.likes]).map((item, i) => (
                      <Typography key={i} sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>• {item}</Typography>
                    ))}
                  </Box>
                  <Box sx={{ flex: 1, minWidth: 180 }}>
                    <Typography sx={{ fontSize: '0.65rem', fontWeight: 600, color: '#f87171', mb: 0.5 }}>Dislikes</Typography>
                    {(Array.isArray(selectedResult.dislikes) ? selectedResult.dislikes : [selectedResult.dislikes]).map((item, i) => (
                      <Typography key={i} sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>• {item}</Typography>
                    ))}
                  </Box>
                  <Box sx={{ flex: 1, minWidth: 180 }}>
                    <Typography sx={{ fontSize: '0.65rem', fontWeight: 600, color: '#fbbf24', mb: 0.5 }}>Suggestions</Typography>
                    {(Array.isArray(selectedResult.suggestions) ? selectedResult.suggestions : [selectedResult.suggestions]).map((item, i) => (
                      <Typography key={i} sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>• {item}</Typography>
                    ))}
                  </Box>
                </Box>

                {selectedResult.accessibility_concerns && (
                  <Box sx={{ mt: 1.5 }}>
                    <Typography sx={{ fontSize: '0.65rem', fontWeight: 600, color: '#fbbf24', mb: 0.3 }}>Accessibility</Typography>
                    <Typography sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>{selectedResult.accessibility_concerns}</Typography>
                  </Box>
                )}
              </Paper>
            )}
          </>
        )}
      </Box>
    </Box>
  )
}
