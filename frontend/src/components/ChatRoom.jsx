import React, { useState, useEffect, useRef } from 'react'
import {
  Box, TextField, IconButton, Typography, Chip, Select, MenuItem,
  CircularProgress, Paper, Tooltip,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import PersonIcon from '@mui/icons-material/Person'
import ModelTrainingIcon from '@mui/icons-material/ModelTraining'
import AttachMoneyIcon from '@mui/icons-material/AttachMoney'
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import DescriptionIcon from '@mui/icons-material/Description'
import BubbleChartIcon from '@mui/icons-material/BubbleChart'
import { getMessages, sendMessage, getRoom } from '../api/client'
import useWebSocket from '../hooks/useWebSocket'
import ConnectorsPanel from './ConnectorsPanel'
import ArtifactsPanel from './ArtifactsPanel'
import GraphPanel from './GraphPanel'

const MODEL_SHORT = {
  'anthropic/claude-sonnet-4': 'Sonnet',
  'anthropic/claude-3.5-haiku': 'Haiku',
  'anthropic/claude-3.5-sonnet': 'Sonnet 3.5',
  'anthropic/claude-3.7-sonnet': 'Sonnet 3.7',
  'openai/gpt-4o': 'GPT-4o',
  'openai/gpt-4o-mini': '4o-mini',
  'google/gemini-2.0-flash-001': 'Flash',
  'google/gemini-2.0-pro-exp-02-05': 'Gemini Pro',
}

const ALL_MODELS = Object.keys(MODEL_SHORT)

function stripMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^[-*+]\s+/gm, '• ')
    .replace(/`(.*?)`/g, '$1')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
}

export default function ChatRoom({ roomId, user }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [room, setRoom] = useState(null)
  const [modelOverride, setModelOverride] = useState('')
  const [aiThinking, setAiThinking] = useState(false)
  const [showPanel, setShowPanel] = useState(false)
  const [panelView, setPanelView] = useState('connectors') // 'connectors' | 'artifacts' | 'graph'
  const [mentionAnchor, setMentionAnchor] = useState(null) // {open, filter, cursorPos}
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const { lastMessage: wsMessage, onlineUsers, isConnected } = useWebSocket(roomId)

  const loadMessages = () => getMessages(roomId).then(setMessages).catch(console.error)
  const loadRoom = () => getRoom(roomId).then(setRoom).catch(console.error)

  useEffect(() => {
    loadMessages()
    loadRoom()
  }, [roomId])

  useEffect(() => {
    if (!wsMessage) return
    if (wsMessage.type === 'message') {
      setMessages(prev => {
        if (prev.some(m => m.message_id === wsMessage.message_id)) return prev
        return [...prev, wsMessage]
      })
      if (wsMessage.author_type === 'ai') loadRoom()
    } else if (wsMessage.type === 'ai_thinking') {
      setAiThinking(true)
    } else if (wsMessage.type === 'ai_done') {
      setAiThinking(false)
    }
  }, [wsMessage])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, aiThinking])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const content = input
    setInput('')
    setLoading(true)

    const tempMsg = {
      message_id: 'temp-' + Date.now(),
      author_type: 'human',
      author_name: user.display_name || user.email,
      content,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, tempMsg])

    try {
      const res = await sendMessage(roomId, content, modelOverride || null)
      setMessages(prev => {
        const filtered = prev.filter(m => m.message_id !== tempMsg.message_id)
        const newMessages = [...filtered, {
          message_id: res.message_id,
          author_type: 'human',
          author_name: user.display_name || user.email,
          content: res.content,
          created_at: res.created_at || new Date().toISOString(),
        }]
        if (res.ai_response) {
          newMessages.push({
            message_id: res.ai_response.message_id,
            author_type: 'ai',
            author_name: 'Bachman',
            content: res.ai_response.content,
            model_used: res.ai_response.model,
            cost: res.ai_response.cost,
            entities_extracted: res.ai_response.entities_extracted,
            created_at: new Date().toISOString(),
          })
        }
        return newMessages
      })
      loadRoom()
    } catch (err) {
      alert('Failed to send: ' + err.message)
      setMessages(prev => prev.filter(m => m.message_id !== tempMsg.message_id))
    } finally {
      setLoading(false)
    }
  }

  const defaultModel = room?.default_model || ''
  const activeModel = modelOverride || defaultModel
  const spend = room?.spend || {}

  return (
    <Box sx={{ flex: 1, display: 'flex', height: '100vh' }}>
      {/* Main chat area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Room Header */}
        <Box sx={{
          px: 3, py: 1.5, borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          bgcolor: 'rgba(13, 17, 23, 0.8)', backdropFilter: 'blur(8px)',
        }}>
          <Box>
            <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.95rem', fontWeight: 600 }}>
              {room?.name || 'Loading...'}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                {room?.members?.length || 0} member{room?.members?.length !== 1 ? 's' : ''}
              </Typography>
              {onlineUsers.length > 0 && (
                <>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>·</Typography>
                  <FiberManualRecordIcon sx={{ fontSize: '0.5rem', color: '#4ade80' }} />
                  <Typography sx={{ fontSize: '0.7rem', color: '#4ade80' }}>
                    {onlineUsers.length} online
                  </Typography>
                </>
              )}
              {isConnected && (
                <Tooltip title="Real-time connected">
                  <FiberManualRecordIcon sx={{ fontSize: '0.4rem', color: '#4ade80', ml: 0.5 }} />
                </Tooltip>
              )}
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {spend.total_cost > 0 && (
              <Chip
                icon={<AttachMoneyIcon sx={{ fontSize: '0.8rem' }} />}
                label={`$${Number(spend.total_cost).toFixed(4)}`}
                size="small"
                sx={{ fontSize: '0.7rem', bgcolor: 'rgba(110, 231, 183, 0.08)', color: 'primary.main' }}
              />
            )}
            <Chip
              icon={<ModelTrainingIcon sx={{ fontSize: '0.8rem' }} />}
              label={MODEL_SHORT[activeModel] || 'Model'}
              size="small"
              sx={{ fontSize: '0.7rem', bgcolor: 'rgba(129, 140, 248, 0.1)', color: 'secondary.main' }}
            />
            <Tooltip title="Connectors & Entities">
              <IconButton size="small" onClick={() => {
                if (showPanel && panelView === 'connectors') setShowPanel(false)
                else { setShowPanel(true); setPanelView('connectors') }
              }}
                sx={{ color: showPanel && panelView === 'connectors' ? 'primary.main' : 'text.secondary' }}>
                <AccountTreeIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Artifacts">
              <IconButton size="small" onClick={() => {
                if (showPanel && panelView === 'artifacts') setShowPanel(false)
                else { setShowPanel(true); setPanelView('artifacts') }
              }}
                sx={{ color: showPanel && panelView === 'artifacts' ? 'secondary.main' : 'text.secondary' }}>
                <DescriptionIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Knowledge Graph">
              <IconButton size="small" onClick={() => {
                if (showPanel && panelView === 'graph') setShowPanel(false)
                else { setShowPanel(true); setPanelView('graph') }
              }}
                sx={{ color: showPanel && panelView === 'graph' ? '#38bdf8' : 'text.secondary' }}>
                <BubbleChartIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Messages */}
        <Box sx={{ flex: 1, overflow: 'auto', px: 3, py: 2 }}>
          {messages.length === 0 && (
            <Box sx={{ textAlign: 'center', py: 8, color: 'text.secondary' }}>
              <SmartToyIcon sx={{ fontSize: '2.5rem', mb: 1, opacity: 0.3 }} />
              <Typography sx={{ fontSize: '0.85rem' }}>
                Start a conversation. Type <b>@Bachman</b> to bring the AI into the chat.
              </Typography>
            </Box>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.message_id} msg={msg} isOwnMessage={msg.author_type === 'human' && msg.author_name === (user.display_name || user.email)} />
          ))}

          {(loading || aiThinking) && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1, color: 'text.secondary' }}>
              <CircularProgress size={16} sx={{ color: 'primary.main' }} />
              <Typography sx={{ fontSize: '0.8rem' }}>
                {aiThinking ? 'Bachman is thinking...' : 'Sending...'}
              </Typography>
            </Box>
          )}

          <div ref={bottomRef} />
        </Box>

        {/* Input */}
        <Box sx={{ px: 3, py: 2, borderTop: '1px solid rgba(255,255,255,0.06)', bgcolor: 'rgba(13, 17, 23, 0.8)' }}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
            <Tooltip title="Override model for this message">
              <Select
                size="small" displayEmpty
                value={modelOverride}
                onChange={(e) => setModelOverride(e.target.value)}
                sx={{
                  minWidth: 90, fontSize: '0.7rem', height: 40,
                  '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1)' },
                }}
                renderValue={(v) => v ? MODEL_SHORT[v] : 'Default'}
              >
                <MenuItem value="" sx={{ fontSize: '0.8rem' }}>Default ({MODEL_SHORT[defaultModel]})</MenuItem>
                {ALL_MODELS.map((m) => (
                  <MenuItem key={m} value={m} sx={{ fontSize: '0.8rem' }}>{MODEL_SHORT[m]}</MenuItem>
                ))}
              </Select>
            </Tooltip>

            <Box sx={{ flex: 1, position: 'relative' }}>
              {/* Mention autocomplete dropdown */}
              {mentionAnchor?.open && (() => {
                const filter = (mentionAnchor.filter || '').toLowerCase()
                const members = (room?.members || []).map(m => ({
                  id: m.user_id || m.email,
                  name: m.display_name || m.email,
                  type: 'member',
                }))
                const bachman = { id: 'bachman', name: 'Bachman', type: 'ai' }
                const all = [bachman, ...members].filter(p =>
                  p.name.toLowerCase().includes(filter)
                )
                if (all.length === 0) return null
                return (
                  <Paper sx={{
                    position: 'absolute', bottom: '100%', left: 0, mb: 0.5,
                    width: 220, maxHeight: 180, overflow: 'auto',
                    bgcolor: '#161b22', border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 1.5, zIndex: 10, py: 0.5,
                  }}>
                    {all.map((person, i) => (
                      <Box key={person.id}
                        onClick={() => {
                          // Replace @partial with @Name
                          const before = input.substring(0, mentionAnchor.atPos)
                          const after = input.substring(mentionAnchor.cursorPos)
                          setInput(before + '@' + person.name + ' ' + after)
                          setMentionAnchor(null)
                          inputRef.current?.focus()
                        }}
                        sx={{
                          px: 1.5, py: 0.7, cursor: 'pointer',
                          display: 'flex', alignItems: 'center', gap: 1,
                          '&:hover': { bgcolor: 'rgba(110, 231, 183, 0.08)' },
                        }}>
                        <SmartToyIcon sx={{
                          fontSize: '0.9rem',
                          color: person.type === 'ai' ? '#6ee7b7' : '#818cf8',
                          display: person.type === 'ai' ? 'block' : 'none',
                        }} />
                        <PersonIcon sx={{
                          fontSize: '0.9rem',
                          color: '#818cf8',
                          display: person.type === 'member' ? 'block' : 'none',
                        }} />
                        <Typography sx={{ fontSize: '0.8rem', fontWeight: person.type === 'ai' ? 600 : 400 }}>
                          {person.name}
                        </Typography>
                        {person.type === 'ai' && (
                          <Chip label="AI" size="small" sx={{ fontSize: '0.5rem', height: 14, bgcolor: 'rgba(110, 231, 183, 0.15)', color: '#6ee7b7' }} />
                        )}
                      </Box>
                    ))}
                  </Paper>
                )
              })()}

              <TextField
                fullWidth size="small" multiline maxRows={4}
                inputRef={inputRef}
                placeholder="Message... (type @Bachman to invoke AI)"
                value={input}
                onChange={(e) => {
                  const val = e.target.value
                  setInput(val)

                  // Detect @ mentions
                  const cursorPos = e.target.selectionStart || val.length
                  const textBefore = val.substring(0, cursorPos)
                  const atMatch = textBefore.match(/@(\w*)$/)

                  if (atMatch) {
                    setMentionAnchor({
                      open: true,
                      filter: atMatch[1],
                      atPos: textBefore.lastIndexOf('@'),
                      cursorPos,
                    })
                  } else {
                    setMentionAnchor(null)
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') { setMentionAnchor(null); return }
                  if (e.key === 'Enter' && !e.shiftKey && !mentionAnchor?.open) { e.preventDefault(); handleSend() }
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderColor: 'rgba(255,255,255,0.1)',
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'primary.main' },
                  },
                }}
              />
            </Box>

            <IconButton onClick={handleSend} disabled={!input.trim() || loading}
              sx={{
                bgcolor: 'primary.main', color: '#0a0e17', width: 40, height: 40,
                '&:hover': { bgcolor: '#5ddba8' },
                '&.Mui-disabled': { bgcolor: 'rgba(110, 231, 183, 0.15)', color: 'rgba(10, 14, 23, 0.5)' },
              }}>
              <SendIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      </Box>

      {/* Right panel */}
      {showPanel && (
        <Box sx={{
          width: panelView === 'graph' ? 420 : 320,
          borderLeft: '1px solid rgba(255,255,255,0.06)',
          bgcolor: '#0d1117', flexShrink: 0,
          transition: 'width 0.2s ease',
        }}>
          {panelView === 'connectors' ? (
            <ConnectorsPanel roomId={roomId} />
          ) : panelView === 'artifacts' ? (
            <ArtifactsPanel roomId={roomId} />
          ) : (
            <GraphPanel roomId={roomId} />
          )}
        </Box>
      )}
    </Box>
  )
}


function MessageBubble({ msg, isOwnMessage }) {
  const isAI = msg.author_type === 'ai'
  const isSystem = msg.author_type === 'system'

  if (isSystem) {
    return (
      <Box sx={{ textAlign: 'center', py: 1 }}>
        <Typography sx={{ fontSize: '0.75rem', color: 'warning.main', fontStyle: 'italic' }}>
          {msg.content}
        </Typography>
      </Box>
    )
  }

  const formatTimestamp = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z')
    const date = d.toLocaleDateString([], { month: 'short', day: 'numeric' })
    const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const tz = d.toLocaleTimeString([], { timeZoneName: 'short' }).split(' ').pop()
    return `${date}, ${time} ${tz}`
  }

  const timestamp = formatTimestamp(msg.created_at)

  return (
    <Box sx={{ mb: 2, display: 'flex', flexDirection: 'column', alignItems: isOwnMessage ? 'flex-end' : 'flex-start' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.3 }}>
        {isAI ? (
          <SmartToyIcon sx={{ fontSize: '0.8rem', color: 'primary.main' }} />
        ) : (
          <PersonIcon sx={{ fontSize: '0.8rem', color: 'text.secondary' }} />
        )}
        <Typography sx={{ fontSize: '0.7rem', fontWeight: 600, color: isAI ? 'primary.main' : 'text.secondary' }}>
          {msg.author_name || (isAI ? 'Bachman' : 'Unknown')}
        </Typography>
        {msg.model_used && (
          <Chip label={MODEL_SHORT[msg.model_used] || msg.model_used} size="small"
            sx={{ fontSize: '0.55rem', height: 16, bgcolor: 'rgba(129, 140, 248, 0.1)', color: 'secondary.main' }} />
        )}
        <Typography sx={{ fontSize: '0.6rem', color: 'text.secondary' }}>{timestamp}</Typography>
      </Box>

      <Paper sx={{
        px: 2, py: 1.2, maxWidth: '80%',
        bgcolor: isAI ? 'rgba(110, 231, 183, 0.06)' : isOwnMessage ? 'rgba(129, 140, 248, 0.08)' : 'rgba(255,255,255,0.04)',
        border: isAI ? '1px solid rgba(110, 231, 183, 0.12)' : '1px solid rgba(255,255,255,0.06)',
        borderRadius: 2,
      }}>
        <Typography sx={{ fontSize: '0.85rem', lineHeight: 1.6, whiteSpace: 'pre-wrap', fontFamily: '"DM Sans", sans-serif' }}>
          {isAI ? stripMarkdown(msg.content) : msg.content}
        </Typography>
      </Paper>

      {msg.entities_extracted && msg.entities_extracted.length > 0 && (
        <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, flexWrap: 'wrap' }}>
          {msg.entities_extracted.slice(0, 5).map((eid) => (
            <Chip key={eid} label={eid} size="small" clickable
              onClick={() => alert(`Entity: ${eid}\n\nThis will open the graph panel in a future update.`)}
              sx={{
                fontSize: '0.55rem', height: 18,
                bgcolor: 'rgba(110, 231, 183, 0.08)', color: 'primary.main',
                cursor: 'pointer', '&:hover': { bgcolor: 'rgba(110, 231, 183, 0.18)' },
              }} />
          ))}
          {msg.entities_extracted.length > 5 && (
            <Chip label={`+${msg.entities_extracted.length - 5} more`} size="small"
              sx={{ fontSize: '0.55rem', height: 18, color: 'text.secondary' }} />
          )}
        </Box>
      )}
    </Box>
  )
}
