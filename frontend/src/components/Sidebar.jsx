import React, { useState, useEffect } from 'react'
import {
  Box, List, ListItemButton, ListItemText, Typography, IconButton,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button,
  Select, MenuItem, FormControl, InputLabel, Paper,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import LogoutIcon from '@mui/icons-material/Logout'
import TagIcon from '@mui/icons-material/Tag'
import TravelExploreIcon from '@mui/icons-material/TravelExplore'
import GroupsIcon from '@mui/icons-material/Groups'
import CloseIcon from '@mui/icons-material/Close'
import { listRooms, createRoom, listModels } from '../api/client'

const MODEL_LABELS = {
  'anthropic/claude-sonnet-4': 'Claude Sonnet',
  'anthropic/claude-3.5-haiku': 'Claude Haiku',
  'anthropic/claude-3.5-sonnet': 'Claude Sonnet 3.5',
  'anthropic/claude-3.7-sonnet': 'Claude Sonnet 3.7',
  'openai/gpt-4o': 'GPT-4o',
  'openai/gpt-4o-mini': 'GPT-4o Mini',
  'google/gemini-2.0-flash-001': 'Gemini Flash',
  'google/gemini-2.0-pro-exp-02-05': 'Gemini Pro',
}

export default function Sidebar({ user, activeRoomId, onSelectRoom, onLogout }) {
  const [rooms, setRooms] = useState([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newModel, setNewModel] = useState('anthropic/claude-sonnet-4')
  const [autoVendrOpen, setAutoVendrOpen] = useState(false)

  const loadRooms = () => listRooms().then(setRooms).catch(console.error)

  useEffect(() => {
    loadRooms()
  }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      const room = await createRoom(newName, '', newModel)
      setDialogOpen(false)
      setNewName('')
      loadRooms()
      onSelectRoom(room.room_id)
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <Box sx={{
      width: 280, borderRight: '1px solid rgba(255,255,255,0.06)',
      display: 'flex', flexDirection: 'column', bgcolor: '#0d1117',
    }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box>
          <Typography sx={{ fontFamily: '"JetBrains Mono"', fontSize: '0.85rem', color: 'primary.main', fontWeight: 600 }}>
            Darwin Evolve β
          </Typography>
          <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
            {user.display_name || user.email}
          </Typography>
        </Box>
        <Box>
          <IconButton size="small" onClick={() => setDialogOpen(true)} sx={{ color: 'primary.main' }}>
            <AddIcon fontSize="small" />
          </IconButton>
          <IconButton size="small" onClick={onLogout} sx={{ color: 'text.secondary' }}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      {/* autoVendr */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <Button
          fullWidth
          onClick={() => setAutoVendrOpen(true)}
          sx={{
            py: 1, borderRadius: 2,
            background: 'linear-gradient(135deg, rgba(110, 231, 183, 0.12) 0%, rgba(129, 140, 248, 0.12) 100%)',
            border: '1px solid rgba(110, 231, 183, 0.2)',
            color: '#6ee7b7',
            fontFamily: '"JetBrains Mono"',
            fontSize: '0.8rem',
            fontWeight: 700,
            letterSpacing: '0.05em',
            textTransform: 'none',
            '&:hover': {
              background: 'linear-gradient(135deg, rgba(110, 231, 183, 0.2) 0%, rgba(129, 140, 248, 0.2) 100%)',
              border: '1px solid rgba(110, 231, 183, 0.35)',
            },
          }}
        >
          autoVendr
        </Button>
      </Box>

      {/* autoVendr Overlay */}
      {autoVendrOpen && (
        <Box sx={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          bgcolor: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(8px)',
          zIndex: 1300, display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
          onClick={() => setAutoVendrOpen(false)}
        >
          <Box onClick={(e) => e.stopPropagation()} sx={{ width: 400 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography sx={{
                fontFamily: '"JetBrains Mono"', fontSize: '1.3rem', fontWeight: 700,
                color: '#6ee7b7',
              }}>
                autoVendr
              </Typography>
              <IconButton size="small" onClick={() => setAutoVendrOpen(false)} sx={{ color: 'text.secondary' }}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>

            <Paper
              sx={{
                px: 3, py: 2.5, mb: 1.5, cursor: 'pointer',
                bgcolor: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(110, 231, 183, 0.15)',
                borderRadius: 2,
                '&:hover': {
                  bgcolor: 'rgba(110, 231, 183, 0.06)',
                  border: '1px solid rgba(110, 231, 183, 0.35)',
                },
              }}
              onClick={() => { setAutoVendrOpen(false); alert('Research Agent — coming soon') }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <TravelExploreIcon sx={{ fontSize: '1.5rem', color: '#6ee7b7' }} />
                <Box>
                  <Typography sx={{ fontSize: '0.95rem', fontWeight: 600 }}>
                    Research Agent
                  </Typography>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', mt: 0.3 }}>
                    Monitors your market and industry. Keeps you up to date on competitors, trends, and emerging signals.
                  </Typography>
                </Box>
              </Box>
            </Paper>

            <Paper
              sx={{
                px: 3, py: 2.5, cursor: 'pointer',
                bgcolor: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(129, 140, 248, 0.15)',
                borderRadius: 2,
                '&:hover': {
                  bgcolor: 'rgba(129, 140, 248, 0.06)',
                  border: '1px solid rgba(129, 140, 248, 0.35)',
                },
              }}
              onClick={() => { setAutoVendrOpen(false); alert('Customer Clinic Agent — coming soon') }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <GroupsIcon sx={{ fontSize: '1.5rem', color: '#818cf8' }} />
                <Box>
                  <Typography sx={{ fontSize: '0.95rem', fontWeight: 600 }}>
                    Customer Clinic Agent
                  </Typography>
                  <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary', mt: 0.3 }}>
                    Reviews your work-in-progress against customer needs. Flags when you're drifting from what users want.
                  </Typography>
                </Box>
              </Box>
            </Paper>
          </Box>
        </Box>
      )}

      {/* Room List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <Typography sx={{ px: 2, pt: 2, pb: 1, fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'text.secondary' }}>
          Rooms
        </Typography>
        <List dense disablePadding>
          {rooms.map((room) => (
            <ListItemButton
              key={room.room_id}
              selected={room.room_id === activeRoomId}
              onClick={() => onSelectRoom(room.room_id)}
              sx={{
                mx: 1, borderRadius: 1.5, mb: 0.5,
                '&.Mui-selected': { bgcolor: 'rgba(110, 231, 183, 0.08)' },
              }}
            >
              <TagIcon sx={{ fontSize: '1rem', mr: 1, color: 'text.secondary' }} />
              <ListItemText
                primary={room.name}
                secondary={MODEL_LABELS[room.default_model] || room.default_model}
                primaryTypographyProps={{ fontSize: '0.85rem', fontWeight: 500 }}
                secondaryTypographyProps={{ fontSize: '0.65rem' }}
              />
            </ListItemButton>
          ))}
        </List>
        {rooms.length === 0 && (
          <Typography sx={{ px: 2, py: 4, textAlign: 'center', color: 'text.secondary', fontSize: '0.8rem' }}>
            No rooms yet. Create one to start.
          </Typography>
        )}
      </Box>

      {/* Create Room Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontFamily: '"JetBrains Mono"', fontSize: '1rem' }}>
          New Room
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus fullWidth label="Room Name" value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="e.g., HVAC Redesign, Cluster Notifications"
            sx={{ mt: 1, mb: 2 }} size="small"
          />
          <FormControl fullWidth size="small">
            <InputLabel>Default Model</InputLabel>
            <Select value={newModel} onChange={(e) => setNewModel(e.target.value)} label="Default Model">
              {Object.entries(MODEL_LABELS).map(([value, label]) => (
                <MenuItem key={value} value={value}>{label}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} sx={{ color: 'text.secondary' }}>Cancel</Button>
          <Button onClick={handleCreate} variant="contained"
            sx={{ bgcolor: 'primary.main', color: '#0a0e17' }}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
