import React, { useState, useRef } from 'react'
import {
  Box, Typography, Button, TextField, LinearProgress, Paper,
  IconButton, Slider, Tabs, Tab,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import TravelExploreIcon from '@mui/icons-material/TravelExplore'
import NewspaperIcon from '@mui/icons-material/Newspaper'
import PodcastsIcon from '@mui/icons-material/Podcasts'
import StorageIcon from '@mui/icons-material/Storage'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import SendIcon from '@mui/icons-material/Send'
import DownloadIcon from '@mui/icons-material/Download'
import VolumeUpIcon from '@mui/icons-material/VolumeUp'
import { generateResearch, uploadDataset, queryDataset, generatePodcastAudio } from '../api/client'

function TabPanel({ children, value, index }) {
  return value === index ? <Box sx={{ pt: 2 }}>{children}</Box> : null
}

export default function ResearchAgentPanel({ onBack }) {
  const [query, setQuery] = useState('')
  const [maxPapers, setMaxPapers] = useState(50)
  const [researchLoading, setResearchLoading] = useState(false)
  const [researchResults, setResearchResults] = useState(null)
  const [outputTab, setOutputTab] = useState(0)
  const [audioLoading, setAudioLoading] = useState(false)
  const [audioUrl, setAudioUrl] = useState(null)
  const [abortController, setAbortController] = useState(null)

  const [dbId, setDbId] = useState(null)
  const [dbInfo, setDbInfo] = useState(null)
  const [dataQuery, setDataQuery] = useState('')
  const [dataLoading, setDataLoading] = useState(false)
  const [dataResult, setDataResult] = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const fileRef = useRef()

  const [mainTab, setMainTab] = useState(0)

  const handleGenerate = async () => {
    if (!query.trim()) return
    setResearchLoading(true)
    setResearchResults(null)
    try {
      const data = await generateResearch(query, maxPapers)
      setResearchResults(data)
    } catch (err) {
      alert(`Research failed: ${err.message}`)
    } finally {
      setResearchLoading(false)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploadLoading(true)
    try {
      const data = await uploadDataset(file)
      setDbId(data.db_id)
      setDbInfo(data)
    } catch (err) {
      alert(`Upload failed: ${err.message}`)
    } finally {
      setUploadLoading(false)
    }
  }

  const handleDataQuery = async () => {
    if (!dbId || !dataQuery.trim()) return
    setDataLoading(true)
    setDataResult(null)
    try {
      const data = await queryDataset(dbId, dataQuery)
      setDataResult(data)
    } catch (err) {
      alert(`Query failed: ${err.message}`)
    } finally {
      setDataLoading(false)
    }
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <Box sx={{
        px: 3, py: 2, borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', alignItems: 'center', gap: 1.5,
      }}>
        <IconButton size="small" onClick={onBack} sx={{ color: 'text.secondary' }}>
          <ArrowBackIcon fontSize="small" />
        </IconButton>
        <TravelExploreIcon sx={{ color: '#6ee7b7' }} />
        <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '1rem', fontWeight: 700, color: '#6ee7b7' }}>
          Research Agent
        </Typography>
      </Box>

      {/* Main Tabs */}
      <Box sx={{ px: 3, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <Tabs value={mainTab} onChange={(_, v) => setMainTab(v)} sx={{
          minHeight: 36,
          '& .MuiTab-root': { minHeight: 36, fontSize: '0.7rem', fontFamily: '"JetBrains Mono"', textTransform: 'none', color: 'text.secondary' },
          '& .Mui-selected': { color: '#6ee7b7' },
          '& .MuiTabs-indicator': { bgcolor: '#6ee7b7' },
        }}>
          <Tab icon={<NewspaperIcon sx={{ fontSize: '0.9rem' }} />} iconPosition="start" label="Research Generator" />
          <Tab icon={<StorageIcon sx={{ fontSize: '0.9rem' }} />} iconPosition="start" label="Data Analyst" />
        </Tabs>
      </Box>

      {/* Research Generator Tab */}
      <TabPanel value={mainTab} index={0}>
        <Box sx={{ flex: 1, overflow: 'auto', px: 3, pb: 3 }}>
          {/* Search Controls */}
          <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <Box sx={{ flex: 1, minWidth: 250 }}>
              <TextField
                fullWidth size="small" label="Research Topics"
                placeholder="e.g., HMI, automotive AI, voice interface"
                value={query} onChange={e => setQuery(e.target.value)}
                multiline rows={2}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              />
            </Box>
            <Box sx={{ width: 160 }}>
              <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary', mb: 0.5 }}>Max Papers: {maxPapers}</Typography>
              <Slider
                value={maxPapers} onChange={(_, v) => setMaxPapers(v)}
                min={10} max={100} step={10}
                size="small"
                sx={{ color: '#6ee7b7' }}
              />
            </Box>
            <Button
              variant="contained"
              onClick={handleGenerate}
              disabled={researchLoading || !query.trim()}
              sx={{
                borderRadius: 2, py: 1.2, px: 3,
                bgcolor: '#6ee7b7', color: '#0a0e17',
                fontFamily: '"JetBrains Mono"', fontWeight: 700,
                fontSize: '0.75rem', textTransform: 'none',
                '&:hover': { bgcolor: '#34d399' },
              }}
            >
              {researchLoading ? 'Generating...' : 'Generate'}
            </Button>
          </Box>

          {researchLoading && (
            <LinearProgress sx={{
              mb: 2, height: 4, borderRadius: 2, bgcolor: 'rgba(110,231,183,0.1)',
              '& .MuiLinearProgress-bar': { bgcolor: '#6ee7b7' },
            }} />
          )}

          {/* Results */}
          {researchResults && (
            <>
              {/* Status */}
              <Paper sx={{ px: 2, py: 1.5, mb: 2, borderRadius: 2, bgcolor: 'rgba(110,231,183,0.04)', border: '1px solid rgba(110,231,183,0.15)' }}>
                <Typography sx={{ fontSize: '0.65rem', color: '#6ee7b7' }}>
                  ✅ Searched {researchResults.papers_searched} papers · Top 5 selected · Newsletter + Podcast generated
                </Typography>
              </Paper>

              {/* Top Papers */}
              <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.75rem', fontWeight: 600, mb: 1 }}>
                Top Papers
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 2 }}>
                {researchResults.top_papers?.map((p, i) => (
                  <Paper key={i} sx={{ px: 2, py: 1, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                      <Box sx={{ flex: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.3 }}>
                          <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.55rem', color: '#6ee7b7', fontWeight: 700 }}>
                            #{i + 1}
                          </Typography>
                          <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.55rem', color: 'text.secondary' }}>
                            Score: {p.score}
                          </Typography>
                        </Box>
                        <Typography sx={{ fontSize: '0.7rem', fontWeight: 500, mb: 0.3 }}>{p.title}</Typography>
                        <Typography sx={{ fontSize: '0.55rem', color: 'text.secondary' }}>
                          {p.authors?.join(', ')} · {p.published}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={() => window.open(p.pdf_url || p.url, '_blank')}
                        sx={{
                          color: '#6ee7b7', mt: 0.5,
                          bgcolor: 'rgba(110,231,183,0.08)',
                          '&:hover': { bgcolor: 'rgba(110,231,183,0.2)' },
                        }}
                      >
                        <DownloadIcon sx={{ fontSize: '1rem' }} />
                      </IconButton>
                    </Box>
                  </Paper>
                ))}
              </Box>

              {/* Newsletter / Podcast Tabs */}
              <Tabs value={outputTab} onChange={(_, v) => setOutputTab(v)} sx={{
                minHeight: 32, mb: 1,
                '& .MuiTab-root': { minHeight: 32, fontSize: '0.65rem', fontFamily: '"JetBrains Mono"', textTransform: 'none', color: 'text.secondary' },
                '& .Mui-selected': { color: '#6ee7b7' },
                '& .MuiTabs-indicator': { bgcolor: '#6ee7b7' },
              }}>
                <Tab icon={<NewspaperIcon sx={{ fontSize: '0.8rem' }} />} iconPosition="start" label="Newsletter" />
                <Tab icon={<PodcastsIcon sx={{ fontSize: '0.8rem' }} />} iconPosition="start" label="Podcast" />
              </Tabs>

              <Paper sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', maxHeight: 400, overflow: 'auto' }}>
                <Typography sx={{
                  fontSize: '0.7rem', color: 'text.secondary',
                  whiteSpace: 'pre-wrap', fontFamily: '"JetBrains Mono"', lineHeight: 1.6,
                }}>
                  {outputTab === 0 ? researchResults.newsletter : researchResults.podcast}
                </Typography>
              </Paper>

              {/* Audio Generation */}
              <Box sx={{ mt: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
                {!audioLoading ? (
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<VolumeUpIcon sx={{ fontSize: '0.9rem' }} />}
                    disabled={!researchResults?.podcast}
                    onClick={async () => {
                      const controller = new AbortController()
                      setAbortController(controller)
                      setAudioLoading(true)
                      setAudioUrl(null)
                      try {
                        const result = await generatePodcastAudio(
                          researchResults.podcast,
                          researchResults.query || 'HMI Research'
                        )
                        const filename = result.audio_path.split('/').pop()
                        setAudioUrl(`/api/vendr/research/podcast/download/${filename}`)
                      } catch (err) {
                        if (err.name !== 'AbortError') {
                          alert(`Audio generation failed: ${err.message}`)
                        }
                      } finally {
                        setAudioLoading(false)
                        setAbortController(null)
                      }
                    }}
                    sx={{
                      borderRadius: 2, py: 1, px: 3,
                      bgcolor: '#6ee7b7', color: '#0a0e17',
                      fontFamily: '"JetBrains Mono"', fontWeight: 700,
                      fontSize: '0.7rem', textTransform: 'none',
                      '&:hover': { bgcolor: '#34d399' },
                    }}
                  >
                    Generate Audio Podcast
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => {
                        if (abortController) abortController.abort()
                        setAudioLoading(false)
                        setAbortController(null)
                      }}
                      sx={{
                        borderRadius: 2, py: 1, px: 3,
                        borderColor: '#f87171', color: '#f87171',
                        fontFamily: '"JetBrains Mono"', fontWeight: 700,
                        fontSize: '0.7rem', textTransform: 'none',
                        '&:hover': { borderColor: '#ef4444', bgcolor: 'rgba(248,113,113,0.08)' },
                      }}
                    >
                      Stop Generation
                    </Button>
                    <Typography sx={{ fontSize: '0.6rem', color: '#fbbf24', fontStyle: 'italic' }}>
                      ⏳ Generating audio via NotebookLM... this takes 2-3 minutes
                    </Typography>
                  </>
                )}
              </Box>

              {audioUrl && (
                <Box sx={{ mt: 2, p: 2, borderRadius: 2, bgcolor: 'rgba(110,231,183,0.04)', border: '1px solid rgba(110,231,183,0.15)' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography sx={{ fontSize: '0.65rem', color: '#6ee7b7', fontWeight: 600 }}>
                      🎙️ Podcast Ready
                    </Typography>
                    <Button
                      size="small"
                      onClick={() => { setAudioUrl(null); setAudioLoading(false) }}
                      sx={{ fontSize: '0.55rem', color: 'text.secondary', textTransform: 'none', minWidth: 'auto' }}
                    >
                      Reset
                    </Button>
                  </Box>
                  <audio controls style={{ width: '100%' }}>
                    <source src={audioUrl} type="audio/mpeg" />
                  </audio>
                </Box>
              )}
            </>
          )}
        </Box>
      </TabPanel>

      {/* Data Analyst Tab */}
      <TabPanel value={mainTab} index={1}>
        <Box sx={{ flex: 1, overflow: 'auto', px: 3, pb: 3 }}>
          {!dbId ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Paper
                onClick={() => fileRef.current?.click()}
                sx={{
                  display: 'inline-flex', flexDirection: 'column', alignItems: 'center',
                  gap: 1.5, px: 6, py: 4, cursor: 'pointer',
                  bgcolor: 'rgba(110,231,183,0.04)',
                  border: '2px dashed rgba(110,231,183,0.2)',
                  borderRadius: 3,
                  '&:hover': { border: '2px dashed rgba(110,231,183,0.5)' },
                }}
              >
                <CloudUploadIcon sx={{ fontSize: '2.5rem', color: '#6ee7b7', opacity: 0.5 }} />
                <Typography sx={{ fontSize: '0.8rem', color: 'text.secondary' }}>
                  Upload a CSV file to start analyzing
                </Typography>
                <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>
                  Click to browse or drag and drop
                </Typography>
              </Paper>
              <input ref={fileRef} type="file" accept=".csv" hidden onChange={handleFileUpload} />
              {uploadLoading && <LinearProgress sx={{ mt: 2, maxWidth: 300, mx: 'auto' }} />}
            </Box>
          ) : (
            <>
              <Paper sx={{ px: 2, py: 1.5, mb: 2, borderRadius: 2, bgcolor: 'rgba(110,231,183,0.04)', border: '1px solid rgba(110,231,183,0.15)' }}>
                <Typography sx={{ fontSize: '0.65rem', color: '#6ee7b7', fontWeight: 600 }}>
                  📊 {dbInfo.table_name} — {dbInfo.row_count} rows · {dbInfo.columns.length} columns
                </Typography>
                <Typography sx={{ fontSize: '0.55rem', color: 'text.secondary', mt: 0.3 }}>
                  Columns: {dbInfo.columns.join(', ')}
                </Typography>
              </Paper>

              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <TextField
                  fullWidth size="small"
                  placeholder="Ask a question about your data..."
                  value={dataQuery} onChange={e => setDataQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleDataQuery() } }}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
                <IconButton
                  onClick={handleDataQuery}
                  disabled={dataLoading || !dataQuery.trim()}
                  sx={{ bgcolor: '#6ee7b7', color: '#0a0e17', borderRadius: 2, '&:hover': { bgcolor: '#34d399' } }}
                >
                  <SendIcon fontSize="small" />
                </IconButton>
              </Box>

              {dataLoading && <LinearProgress sx={{ mb: 2 }} />}

              {dataResult && (
                <Box>
                  <Paper sx={{ px: 2, py: 1.5, mb: 2, borderRadius: 2, bgcolor: 'rgba(129,140,248,0.04)', border: '1px solid rgba(129,140,248,0.15)' }}>
                    <Typography sx={{ fontSize: '0.75rem', color: 'text.primary', lineHeight: 1.6 }}>
                      {dataResult.answer}
                    </Typography>
                  </Paper>

                  <Paper sx={{ px: 2, py: 1, mb: 2, borderRadius: 2, bgcolor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <Typography sx={{ fontSize: '0.55rem', color: 'text.secondary', mb: 0.3, fontWeight: 600 }}>SQL</Typography>
                    <Typography sx={{ fontSize: '0.6rem', color: '#6ee7b7', fontFamily: '"JetBrains Mono"' }}>
                      {dataResult.sql}
                    </Typography>
                  </Paper>

                  {dataResult.rows?.length > 0 && (
                    <Box sx={{ overflow: 'auto', maxHeight: 300 }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.6rem' }}>
                        <thead>
                          <tr>
                            {Object.keys(dataResult.rows[0]).map(col => (
                              <th key={col} style={{
                                textAlign: 'left', padding: '6px 8px',
                                borderBottom: '1px solid rgba(255,255,255,0.1)',
                                color: '#6ee7b7', fontFamily: '"JetBrains Mono"',
                                fontWeight: 600, fontSize: '0.55rem',
                              }}>{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {dataResult.rows.slice(0, 20).map((row, i) => (
                            <tr key={i}>
                              {Object.values(row).map((val, j) => (
                                <td key={j} style={{
                                  padding: '4px 8px',
                                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                                  color: 'rgba(255,255,255,0.7)',
                                  fontFamily: '"JetBrains Mono"',
                                  fontSize: '0.55rem',
                                }}>{val ?? '—'}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <Typography sx={{ fontSize: '0.5rem', color: 'text.secondary', mt: 0.5 }}>
                        Showing {Math.min(20, dataResult.rows.length)} of {dataResult.total_rows} rows
                      </Typography>
                    </Box>
                  )}

                  <Button
                    size="small"
                    onClick={() => { setDbId(null); setDbInfo(null); setDataResult(null); setDataQuery('') }}
                    sx={{ mt: 2, fontSize: '0.6rem', color: 'text.secondary', textTransform: 'none' }}
                  >
                    Upload different dataset
                  </Button>
                </Box>
              )}
            </>
          )}
        </Box>
      </TabPanel>
    </Box>
  )
}