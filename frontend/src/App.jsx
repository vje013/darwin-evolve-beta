import React, { useState, useEffect } from 'react'
import { Box } from '@mui/material'
import { getToken, getMe } from './api/client'
import AuthScreen from './components/AuthScreen'
import Sidebar from './components/Sidebar'
import ChatRoom from './components/ChatRoom'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeRoomId, setActiveRoomId] = useState(null)

  useEffect(() => {
    if (getToken()) {
      getMe()
        .then(setUser)
        .catch(() => setUser(null))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  if (loading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'text.secondary' }}>
        Loading...
      </Box>
    )
  }

  if (!user) {
    return <AuthScreen onAuth={setUser} />
  }

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar
        user={user}
        activeRoomId={activeRoomId}
        onSelectRoom={setActiveRoomId}
        onLogout={() => {
          setUser(null)
          localStorage.removeItem('darwin_token')
        }}
      />
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {activeRoomId ? (
          <ChatRoom roomId={activeRoomId} user={user} />
        ) : (
          <Box sx={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: 1, color: 'text.secondary',
          }}>
            <Box sx={{ fontFamily: '"JetBrains Mono"', fontSize: '1.5rem', color: 'primary.main' }}>
              Darwin Evolve β
            </Box>
            <Box sx={{ fontSize: '0.9rem' }}>Select or create a room to start collaborating</Box>
          </Box>
        )}
      </Box>
    </Box>
  )
}
